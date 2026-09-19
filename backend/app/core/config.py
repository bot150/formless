import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend root if it exists
backend_dir = Path(__file__).resolve().parent.parent.parent
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()


class Settings:
    app_name: str = os.getenv("APP_NAME", "Formless API")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./formless.db")

    # JWT Configuration
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "formless-development-secure-jwt-secret-key-change-in-production-min-32-chars",
    )
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )

    # Google OAuth 2.0 Configuration
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback"
    )


settings = Settings()

