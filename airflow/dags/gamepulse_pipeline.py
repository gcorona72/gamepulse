"""DAG horario de GamePulse: silver (Spark) -> gold (dbt sobre DuckDB).

La ingesta (Twitch, Steam) y bronze son servicios 24/7 de docker compose; Airflow orquesta
las transformaciones por lotes. Cada tarea arranca un contenedor efímero de la imagen
`gamepulse-spark-bronze` en la red de compose, igual que `make silver` / `make gold`.
"""

import os

import pendulum
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG
from docker.types import Mount

IMAGE = "gamepulse-spark-bronze:latest"
NETWORK = "gamepulse_default"
HOST_PROJECT_DIR = os.environ.get("HOST_PROJECT_DIR", "")

COMMON = dict(
    image=IMAGE,
    network_mode=NETWORK,
    docker_url="unix://var/run/docker.sock",
    auto_remove="success",
    mount_tmp_dir=False,
    environment={
        "S3_ENDPOINT": "http://minio:9000",
        "LAKEHOUSE_TARGET": "minio",
        "DUCKDB_S3_ENDPOINT": "minio:9000",
        "DUCKDB_PATH": "/warehouse/gamepulse.duckdb",
    },
)

with DAG(
    dag_id="gamepulse_pipeline",
    description="Silver (Spark) y gold (dbt) cada hora",
    schedule="20 * * * *",  # minuto 20: después del batch horario de Steam (minuto ~9)
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=5)},
    tags=["gamepulse"],
) as dag:
    silver = DockerOperator(
        task_id="silver_spark",
        command="python -m gamepulse.spark.silver_build --days 2",
        mounts=[Mount(source="gamepulse_spark_ivy", target="/root/.ivy2.5.2", type="volume")],
        **COMMON,
    )

    gold = DockerOperator(
        task_id="gold_dbt_build",
        command="dbt build --profiles-dir .",
        working_dir="/app/dbt",
        mounts=[
            Mount(source=f"{HOST_PROJECT_DIR}/warehouse", target="/warehouse", type="bind"),
            Mount(source="gamepulse_duckdb_ext", target="/root/.duckdb", type="volume"),
        ],
        **COMMON,
    )

    silver >> gold
