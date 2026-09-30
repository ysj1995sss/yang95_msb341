from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE = f"sqlite+pysqlite:///{(_API_ROOT / 'data' / 'resumecopilot.db').as_posix()}"
DEV_JWT_SECRET = "dev-secret-change-me"
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # "development" (default) or "production". Production refuses unsafe defaults.
    app_env: str = "development"
    # Local dogfood uses SQLite by default -- no Docker/Postgres required.
    database_url: str = _DEFAULT_SQLITE
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    device_token_expire_minutes: int = 60 * 24 * 30
    # Browser origins allowed to call the API, comma-separated (e.g. the deployed site).
    allowed_origins: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _refuse_unsafe_production_defaults(self) -> "Settings":
        if self.app_env.lower() != "production":
            return self
        problems = []
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < MIN_PRODUCTION_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET must be a private random value of at least {MIN_PRODUCTION_SECRET_LENGTH} characters"
            )
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL must point to a durable server database, not a local SQLite file")
        if problems:
            raise ValueError("Refusing to start in production: " + "; ".join(problems) + ".")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings()
