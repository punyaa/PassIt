from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PASSIT_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+psycopg://passit:passit@localhost:5432/passit"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: str = "local-development-only"
    jwt_algorithm: str = "HS256"
    session_cookie_secure: bool = False

    aws_region: str = "ap-southeast-1"
    aws_profile: str | None = None
    bedrock_model_id: str | None = None
    bedrock_guardrail_id: str | None = None
    bedrock_guardrail_version: str | None = None
    s3_bucket: str | None = None
    s3_prefix: str = "media/"
    cloudfront_domain: str | None = None
    media_signed_url_ttl_seconds: int = 900

    mongodb_uri: str | None = None
    mongodb_database: str = "passit"
    mongodb_atlas_public_key: str | None = None
    mongodb_atlas_private_key: str | None = None
    mongodb_atlas_project_id: str | None = None

    onemap_api_url: str = "https://www.onemap.gov.sg/api"
    onemap_token: str | None = None
    llm_api_url: str | None = None
    llm_api_key: str | None = None
    payment_mode: str = "mock"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
