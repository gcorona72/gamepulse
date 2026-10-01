import pytest

from gamepulse.config import Settings


def test_lakehouse_uri_minio_por_defecto():
    s = Settings(_env_file=None)
    assert s.lakehouse_uri == "s3a://lakehouse"


def test_lakehouse_uri_azure():
    s = Settings(_env_file=None, lakehouse_target="azure", azure_storage_account="gamepulselake17")
    assert s.lakehouse_uri == "abfss://lakehouse@gamepulselake17.dfs.core.windows.net"


def test_azure_sin_cuenta_falla():
    with pytest.raises(ValueError):
        _ = Settings(_env_file=None, lakehouse_target="azure").lakehouse_uri
