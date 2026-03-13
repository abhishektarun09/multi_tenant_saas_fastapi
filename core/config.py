from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    google_client_id: str
    google_client_secret: str

    base_url: str
    better_stack_token: str
    redis_url: str

    aiven_kafka_bootstrap: str
    aiven_kafka_topic: str

    AIVEN_KAFKA_CA_PEM_B64: str
    AIVEN_KAFKA_SERVICE_CERT_B64: str
    AIVEN_KAFKA_SERVICE_KEY_B64: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


env = Settings()
