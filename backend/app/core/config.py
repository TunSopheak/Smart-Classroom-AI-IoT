from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Smart Classroom with AI Monitoring - IoT Project"
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./smart_classroom.db"
    SECRET_KEY: str = "change-this-secret-key-before-production"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
