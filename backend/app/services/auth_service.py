from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth_schema import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)


def register_user(db: Session, request: UserRegisterRequest) -> TokenResponse:
    """Register a new user with email and password, hashing the password and returning a JWT session."""
    normalized_email = request.email.strip().lower()

    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        )

    hashed_pw = hash_password(request.password)
    user = User(
        email=normalized_email,
        password_hash=hashed_pw,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


def authenticate_user(db: Session, request: UserLoginRequest) -> TokenResponse:
    """Authenticate an existing user via email and password, returning a JWT token."""
    normalized_email = request.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


def get_or_create_google_user(
    db: Session,
    google_id: str,
    email: str,
    name: Optional[str] = None,
) -> User:
    """Retrieve existing user by google_id or email, or create a new user linked to Google."""
    normalized_email = email.strip().lower()

    # 1. Check if user with this google_id already exists
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        # 2. Check if user with this email already exists (link account)
        user = db.query(User).filter(User.email == normalized_email).first()
        if user:
            user.google_id = google_id
            db.commit()
            db.refresh(user)
        else:
            # 3. Create new user
            user = User(
                email=normalized_email,
                google_id=google_id,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    # If user does not yet have a profile and Google provided a name, initialize basic profile
    if name and not user.profile:
        from app.models.user import Profile

        new_profile = Profile(
            user_id=user.id,
            name=name.strip(),
        )
        db.add(new_profile)
        db.commit()
        db.refresh(user)

    return user
