from datetime import timedelta
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "local-development-only-not-a-secret"


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
    jwt_secret: str = DEFAULT_JWT_SECRET
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
    cloudfront_key_pair_id: str | None = None
    cloudfront_private_key: str | None = None
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
    llm_model: str | None = None
    llm_timeout_seconds: float = 8.0
    payment_mode: Literal["mock"] = "mock"

    # Database pooling. Tests use NullPool so connections never outlive an event loop.
    database_null_pool: bool = False

    # Integration backends. "local" works with no AWS account; staging and demo switch to the
    # AWS implementations in app/integrations/ once the resources exist.
    storage_backend: Literal["local", "s3"] = "local"
    scheduler_backend: Literal["local", "eventbridge"] = "local"
    public_api_url: str = "http://localhost:8000"
    local_media_dir: str = ".media"

    # EventBridge Scheduler target for the fee-release Lambda (provisioned by Terraform).
    release_lambda_arn: str | None = None
    scheduler_role_arn: str | None = None
    scheduler_group_name: str = "default"

    # Business rules.
    fee_hold_minutes: int = 7 * 24 * 60  # set to 1 in staging so releases fire during demos
    membership_period_days: int = 30  # paid Plus plans run one period, then expire to Saver
    local_release_sweep_seconds: int = 30  # 0 disables the in-process sweep
    free_listing_limit: int = 3
    max_rental_days: int = 90

    @model_validator(mode="after")
    def reject_default_secret_outside_development(self) -> "Settings":
        # Anyone can read the default from the repository and forge a session with it.
        if self.environment != "development" and self.jwt_secret == DEFAULT_JWT_SECRET:
            raise ValueError(
                f"PASSIT_JWT_SECRET must be set when PASSIT_ENVIRONMENT={self.environment}"
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def membership_period(self) -> timedelta:
        return timedelta(days=self.membership_period_days)


@lru_cache
def get_settings() -> Settings:
    return Settings()
