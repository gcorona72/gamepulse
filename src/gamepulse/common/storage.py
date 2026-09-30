"""Escritura de ficheros en bruto en la zona 'landing' del lakehouse (MinIO/S3)."""

import json
from collections.abc import Iterable

import boto3

from gamepulse.config import Settings


def s3_client(settings: Settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


def ensure_bucket(settings: Settings) -> None:
    """Crea el bucket del lakehouse si no existe (idempotente). Sustituye al init con `mc`."""
    client = s3_client(settings)
    try:
        client.head_bucket(Bucket=settings.lakehouse_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.lakehouse_bucket)


def to_jsonl(records: Iterable[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


def put_jsonl(settings: Settings, key: str, records: list[dict]) -> str:
    """Sube una lista de registros como JSON Lines. Devuelve la URI s3a:// del objeto."""
    s3_client(settings).put_object(
        Bucket=settings.lakehouse_bucket,
        Key=key,
        Body=to_jsonl(records),
        ContentType="application/x-ndjson",
    )
    return f"s3a://{settings.lakehouse_bucket}/{key}"
