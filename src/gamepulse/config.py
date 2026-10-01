"""Configuración centralizada: lee variables de entorno y el fichero .env."""

from functools import lru_cache
from typing import Literal

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

    # Destino del lakehouse de Spark: "minio" (local) o "azure" (ADLS Gen2)
    lakehouse_target: Literal["minio", "azure"] = "minio"
    azure_storage_account: str = ""
    azure_storage_key: str = ""
    azure_container: str = "lakehouse"

    # Ingesta
    twitch_top_games: int = 50
    twitch_poll_seconds: int = 60
    twitch_topic: str = "twitch.streams.snapshots"
    steam_poll_seconds: int = 3600

    @property
    def lakehouse_uri(self) -> str:
        """Raíz del lakehouse para Spark: s3a:// (MinIO) o abfss:// (ADLS Gen2)."""
        if self.lakehouse_target == "azure":
            if not self.azure_storage_account:
                raise ValueError("Falta AZURE_STORAGE_ACCOUNT en .env")
            return (
                f"abfss://{self.azure_container}"
                f"@{self.azure_storage_account}.dfs.core.windows.net"
            )
        return f"s3a://{self.lakehouse_bucket}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
