from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE = f"sqlite+pysqlite:///{(_API_ROOT / 'data' / 'resumecopilot.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # Local dogfood uses SQLite by default -- no Docker/Postgres required.
    database_url: str = _DEFAULT_SQLITE
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    device_token_expire_minutes: int = 60 * 24 * 30


def get_settings() -> Settings:
    return Settings()
