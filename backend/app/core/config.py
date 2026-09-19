import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "Formless API")
    environment: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()
