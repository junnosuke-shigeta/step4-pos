from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LOCAL_DEV_SECRET_KEY = "local-development-only-change-this-secret-key"


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Step4 POS API"
    secret_key: str = LOCAL_DEV_SECRET_KEY
    access_token_expire_hours: int = 8

    database_url: str | None = None
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "gen12-mysql-pos"
    db_user: str = "tech0"
    db_password: str = ""

    cors_allow_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @model_validator(mode="after")
    def validate_runtime_settings(self):
        if self.is_production:
            if self.secret_key == LOCAL_DEV_SECRET_KEY or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be set to a secure 32+ character value in production")
            if not self.database_url and not self.db_password:
                raise ValueError("Set DATABASE_URL or DB_PASSWORD when APP_ENV=production")
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"


settings = Settings()
