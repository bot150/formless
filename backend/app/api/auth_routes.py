import logging
import secrets
import urllib.parse

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth_schema import (
    ProfileConfirmRequest,
    ProfileResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserProfileDetailsResponse,
    UserWithProfileResponse,
)
from app.services.aadhaar_service import (
    extract_aadhaar_mock,
    save_or_update_profile,
)
from app.services.auth_service import (
    authenticate_user,
    get_or_create_google_user,
    register_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication & Profile"])

# Google OAuth 2.0 endpoints (stable Google URLs — no discovery needed)
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.post(
    "/api/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def api_register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user with email and password, hashing the password and generating a Formless JWT."""
    return register_user(db=db, request=request)


@router.post(
    "/api/auth/login",
    response_model=TokenResponse,
    summary="Log in an existing user",
)
def api_login(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate user with email and password, returning a Formless JWT."""
    return authenticate_user(db=db, request=request)


@router.get(
    "/api/auth/me",
    response_model=UserWithProfileResponse,
    summary="Get current user details",
)
def api_get_me(
    current_user: User = Depends(get_current_user),
):
    """Return the profile and email of the currently authenticated user."""
    return current_user


# -------------------------------------------------------------
# Google OAuth 2.0  (direct httpx — no Authlib starlette client)
# -------------------------------------------------------------
async def _handle_google_login(request: Request):
    """
    Build the Google OAuth 2.0 authorization URL manually and redirect the
    browser there.  A random CSRF state token is stored in the signed session
    cookie so the callback can validate it.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google OAuth is not configured. "
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
            ),
        )

    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    params = urllib.parse.urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    logger.info(
        "Google OAuth login initiated. "
        "CLIENT_ID loaded: %s | REDIRECT_URI: %s",
        bool(settings.google_client_id),
        settings.google_redirect_uri,
    )
    return RedirectResponse(
        url=f"{_GOOGLE_AUTH_URL}?{params}",
        status_code=status.HTTP_302_FOUND,
    )


async def _handle_google_callback(request: Request, db: Session):
    """
    Exchange the authorization code Google sent back for a Formless JWT.

    Steps
    -----
    1. Validate CSRF state stored in session cookie.
    2. POST code to Google's token endpoint via httpx (direct, no Authlib async).
    3. GET userinfo from Google using the returned access_token.
    4. Find-or-create the local Formless user.
    5. Issue a Formless JWT and redirect to /profile/setup.
    """
    # ── 1. CSRF state check ──────────────────────────────────────────────────
    google_error = request.query_params.get("error")
    if google_error:
        desc = request.query_params.get("error_description", google_error)
        logger.error("Google returned OAuth error: %s — %s", google_error, desc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {desc}",
        )

    incoming_state = request.query_params.get("state", "")
    stored_state = request.session.pop("oauth_state", None)

    state_ok = stored_state and incoming_state == stored_state
    if not state_ok:
        if settings.environment == "development":
            # In local development over plain HTTP some browsers do not reliably
            # send the session cookie on the cross-origin redirect from Google.
            # CSRF is not a realistic threat on localhost, so we log a warning
            # and continue.  In production this would be a hard failure.
            logger.warning(
                "OAuth state mismatch in development mode — continuing anyway. "
                "incoming=%r stored=%r",
                (incoming_state[:8] + "…") if incoming_state else "EMPTY",
                (stored_state[:8] + "…") if stored_state else "MISSING",
            )
        else:
            logger.error(
                "OAuth state mismatch. incoming=%r stored=%r",
                (incoming_state[:8] + "…") if incoming_state else "EMPTY",
                (stored_state[:8] + "…") if stored_state else "MISSING",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "OAuth state mismatch — possible CSRF attack or stale session. "
                    "Please start the login flow again from /api/auth/google/login."
                ),
            )

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code missing from Google callback.",
        )

    # ── 2. Exchange code for tokens ──────────────────────────────────────────
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_resp.status_code != 200:
            try:
                err_body = token_resp.json()
            except Exception:
                err_body = {}
            g_error = err_body.get("error", "unknown")
            g_desc = err_body.get("error_description", "No description from Google.")
            logger.error(
                "Google token exchange failed. Status: %d | Error: %s | Description: %s",
                token_resp.status_code,
                g_error,
                g_desc,
            )
            # Map common Google errors to useful developer messages
            _GOOGLE_ERROR_HINTS = {
                "invalid_grant": (
                    "The authorization code has already been used, is expired, "
                    "or the redirect_uri does not exactly match the one used "
                    "during authorization."
                ),
                "invalid_client": (
                    "The client_id or client_secret is wrong. "
                    "Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
                ),
                "redirect_uri_mismatch": (
                    "The redirect_uri sent during token exchange does not match "
                    "the URI registered in Google Cloud Console. "
                    f"Current value: {settings.google_redirect_uri}"
                ),
                "unauthorized_client": (
                    "This OAuth client is not authorized for this grant type."
                ),
                "access_denied": "The user denied access to the application.",
            }
            hint = _GOOGLE_ERROR_HINTS.get(g_error, g_desc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "google_token_exchange_failed",
                    "google_error": g_error,
                    "message": hint,
                },
            )

        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # ── 3. Fetch Google userinfo ─────────────────────────────────────────
        userinfo_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_resp.status_code != 200:
        logger.error(
            "Failed to fetch Google userinfo. Status: %d",
            userinfo_resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve user information from Google.",
        )

    user_info = userinfo_resp.json()
    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not provide an email address.",
        )
    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile did not contain a user ID (sub).",
        )

    # ── 4. Find / create Formless user ───────────────────────────────────────
    try:
        user = get_or_create_google_user(db=db, google_id=google_id, email=email, name=name)
    except Exception as exc:
        logger.error("User persistence error during Google OAuth: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or retrieve the user account.",
        )

    # ── 5. Issue Formless JWT ────────────────────────────────────────────────
    try:
        jwt_token = create_access_token(user_id=user.id, email=user.email)
    except Exception as exc:
        logger.error("JWT generation error after Google OAuth: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authentication token.",
        )

    logger.info("Google OAuth successful for email: %s", email)
    return RedirectResponse(
        url=f"/profile/setup?token={jwt_token}",
        status_code=status.HTTP_303_SEE_OTHER,
    )





# -------------------------------------------------------------
# Google OAuth 2.0 — route declarations
# -------------------------------------------------------------
@router.get(
    "/api/auth/google/login",
    summary="Initiate Google OAuth 2.0 Login",
)
@router.get(
    "/auth/google/login",
    include_in_schema=False,
)
async def google_login(request: Request):
    return await _handle_google_login(request)


@router.get(
    "/api/auth/google/callback",
    summary="Google OAuth 2.0 Callback",
)
@router.get(
    "/auth/google/callback",
    include_in_schema=False,
)
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    return await _handle_google_callback(request, db)


# -------------------------------------------------------------
# Aadhaar Profile Setup & Confirmation
# -------------------------------------------------------------
@router.post(
    "/api/profile/aadhaar",
    response_model=ProfileResponse,
    summary="Upload Aadhaar card image for local mock extraction",
)
async def upload_aadhaar_card(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Extract profile fields (name, DOB, gender, address) from an Aadhaar card image.

    Requires Formless JWT authentication. Processes file in memory and deletes temporary data.
    """
    file_bytes = await file.read()
    try:
        extracted = extract_aadhaar_mock(file=file, file_bytes=file_bytes)
        return extracted
    finally:
        # Guarantee memory release and file close
        await file.close()


@router.post(
    "/api/profile/confirm",
    response_model=UserProfileDetailsResponse,
    summary="Confirm and save verified profile information",
)
def confirm_profile(
    profile_data: ProfileConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save or update the authenticated user's confirmed profile details."""
    saved_profile = save_or_update_profile(
        db=db,
        user=current_user,
        profile_data=profile_data,
    )
    return saved_profile
