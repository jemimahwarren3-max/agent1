from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "postgresql://haki:haki@localhost:5432/haki_prospecting"
    REDIS_URL: str = "redis://localhost:6379/0"

    GEMINI_API_KEY: str = ""

    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/integrations/google/callback"

    TOKEN_ENCRYPTION_KEY: str = ""

    SEARCH_PROVIDER: str = "google_cse"
    GOOGLE_CSE_API_KEY: str = ""
    GOOGLE_CSE_ENGINE_ID: str = ""

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    COMPANY_NAME: str = "Haki Systems"
    COMPANY_WEBSITE: str = "https://hakisystems.co.zw"
    COMPANY_PHONES: list[str] = ["+263 78 928 7766", "+263 776 727 967"]


settings = Settings()
