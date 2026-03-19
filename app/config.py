from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/mini_agent_platform"
    )
    # Comma-separated pairs: "api-key:tenant-id,api-key2:tenant-id2"
    tenant_keys: str = (
        "key-tenant-alpha:tenant-alpha,"
        "key-tenant-beta:tenant-beta,"
        "key-tenant-gamma:tenant-gamma"
    )


settings = Settings()
