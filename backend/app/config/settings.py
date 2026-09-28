"""One settings object shared by the API, worker and database layer."""

import secrets
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "일본 항공권 지도"
    VERSION: str = "0.3.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    DATABASE_URL: str = "sqlite:///./flights.db"
    DATABASE_ECHO: bool = False
    INIT_DB_ON_STARTUP: bool = True
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(48), min_length=32
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_API_KEY: Optional[str] = None
    ENABLE_EXPERIMENTAL_FEATURES: bool = False

    REDIS_URL: Optional[str] = None
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: int = 6379
    REDIS_USERNAME: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    COLLECTION_ORIGINS: list[str] = [
        "ICN",
        "GMP",
        "PUS",
        "CJJ",
        "TAE",
        "CJU",
        "MWX",
        "YNY",
    ]
    MONTHLY_SAMPLE_STEP: int = Field(3, ge=1, le=7)
    MONTHLY_STALE_TTL: int = Field(604800, ge=3600)
    MONTHLY_JOB_LEASE_SECONDS: int = Field(180, ge=120)
    AMADEUS_REQUESTS_PER_SECOND: int = Field(5, ge=1, le=20)
    MONTHLY_CACHE_TTL: int = Field(3600, ge=60)

    AMADEUS_CLIENT_ID: Optional[str] = None
    AMADEUS_CLIENT_SECRET: Optional[str] = None
    AMADEUS_HOSTNAME: str = "test"
    AMADEUS_BASE_URL: str = "https://test.api.amadeus.com"
    USE_REAL_AMADEUS: bool = False
    ENABLE_DUMMY_FALLBACK: bool = False
    KOREAEXIM_API_KEY: Optional[str] = None
    KOREAEXIM_BASE_URL: str = "https://oapi.koreaexim.go.kr"

    OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2025-04-01-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4.1"
    AZURE_OPENAI_MODEL: str = "gpt-4.1"
    AZURE_OPENAI_MAX_TOKENS: int = 4000
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 4000
    LLM_TEMPERATURE: float = 0.7
    EFFICIENCY_SCORE_CACHE_TTL: int = 3600
    MAX_FLIGHTS_PER_ANALYSIS: int = 10

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @model_validator(mode="after")
    def validate_runtime(self):
        if self.MONTHLY_STALE_TTL < self.MONTHLY_CACHE_TTL:
            raise ValueError(
                "마지막 성공 결과 보관 기간은 갱신 간격 이상이어야 합니다."
            )
        if self.USE_REAL_AMADEUS and not (
            self.AMADEUS_CLIENT_ID and self.AMADEUS_CLIENT_SECRET
        ):
            raise ValueError("실제 검색에는 Amadeus API 키가 필요합니다.")
        if self.is_production:
            if not self.DATABASE_URL.startswith(
                ("postgresql://", "postgresql+psycopg2://")
            ):
                raise ValueError(
                    "운영 수집 조정에는 공유 PostgreSQL 데이터베이스가 필요합니다."
                )
            if self.USE_REAL_AMADEUS and not (self.REDIS_URL or self.REDIS_HOST):
                raise ValueError("운영 공급자 호출량 제한에는 공유 Redis가 필요합니다.")
            if "SECRET_KEY" not in self.model_fields_set:
                raise ValueError("운영 환경의 SECRET_KEY를 설정하세요.")
            if self.ENABLE_DUMMY_FALLBACK:
                raise ValueError("운영 환경에서는 데모 데이터를 사용할 수 없습니다.")
            if self.INIT_DB_ON_STARTUP:
                raise ValueError("운영 환경에서는 마이그레이션을 사용하세요.")
        return self

    @property
    def is_production(self):
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self):
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self):
        return self.ENVIRONMENT in {"test", "testing"}


settings = Settings()
