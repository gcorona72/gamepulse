"""Configuración centralizada: lee variables de entorno y el fichero .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Credenciales
    twitch_client_id: str = ""
    twitch_client_secret: str = ""
    steam_api_key: str = ""

    # Infraestructura
    kafka_bootstrap_servers: str = "localhost:19092"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    lakehouse_bucket: str = "lakehouse"

    # Ingesta
    twitch_top_games: int = 50
    twitch_poll_seconds: int = 60
    twitch_topic: str = "twitch.streams.snapshots"
    steam_poll_seconds: int = 3600

    @property
    def lakehouse_uri(self) -> str:
        """Raíz del lakehouse para Spark (protocolo s3a de Hadoop)."""
        return f"s3a://{self.lakehouse_bucket}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
