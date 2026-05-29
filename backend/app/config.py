from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MOT Nexus"
    # Default: relative path (dev). Override with DATABASE_URL env var in production
    # e.g. DATABASE_URL=sqlite:////opt/mot-nexus/mot_nexus.db
    database_url: str = "sqlite:///./mot_nexus.db"
    lock_timeout_minutes: int = 15
    max_upload_size_mb: int = 100

    model_config = {"env_file": ".env"}


settings = Settings()
