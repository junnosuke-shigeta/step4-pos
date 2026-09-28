from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Step4 POS API"
    secret_key: str = "change-me"
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
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"


settings = Settings()
