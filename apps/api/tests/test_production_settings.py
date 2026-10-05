import pytest

from app.config import DEV_JWT_SECRET, Settings

STRONG = "x" * 40
POSTGRES = "postgresql+psycopg://user:pw@db.example.com/app"


def test_development_keeps_convenient_defaults():
    settings = Settings(app_env="development")
    assert settings.jwt_secret == DEV_JWT_SECRET


@pytest.mark.parametrize(
    "secret, url, message",
    [
        (DEV_JWT_SECRET, POSTGRES, "JWT_SECRET"),
        ("short", POSTGRES, "JWT_SECRET"),
        (STRONG, "sqlite+pysqlite:///data/app.db", "DATABASE_URL"),
    ],
)
def test_production_refuses_unsafe_values(secret, url, message):
    with pytest.raises(ValueError, match=message):
        Settings(app_env="production", jwt_secret=secret, database_url=url)


def test_production_starts_with_a_real_secret_and_database():
    settings = Settings(app_env="production", jwt_secret=STRONG, database_url=POSTGRES,
                        workspace_token_secret=STRONG, allowed_origins="https://app.example.com, https://www.example.com")
    assert settings.cors_origins == ["https://app.example.com", "https://www.example.com"]


def test_production_needs_the_shared_workspace_secret():
    with pytest.raises(ValueError, match="WORKSPACE_TOKEN_SECRET"):
        Settings(app_env="production", jwt_secret=STRONG, database_url=POSTGRES)


def test_the_web_app_deployment_needs_no_database_or_password_secret():
    settings = Settings(app_env="production", legacy_routes=False, workspace_token_secret=STRONG)
    assert settings.database_url.startswith("sqlite") and settings.legacy_routes is False
