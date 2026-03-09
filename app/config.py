from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "ScalableFileUpload"
    APP_ENV: str = "development"

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str

    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,pdf,doc,docx,txt,csv,zip"
    PRESIGNED_URL_EXPIRATION: int = 3600

    DATABASE_URL: str = "sqlite+aiosqlite:///./file_upload.db"

    API_KEY: str = "change-me"

    class Config:
        env_file = ".env"

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
