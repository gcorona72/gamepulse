"""DAG horario de GamePulse: silver (Spark) -> gold (dbt) -> sentimiento (modelo) -> gold de sentimiento.

La ingesta (Twitch, Steam) y bronze son servicios 24/7 de docker compose; Airflow orquesta
las transformaciones por lotes. Cada tarea arranca un contenedor efímero en la red de compose:
- `gamepulse-spark-bronze`: Spark (silver) y dbt (gold).
- `gamepulse-ml`: inferencia del modelo de sentimiento (XLM-RoBERTa, en CPU).
"""

import os

import pendulum
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG
from docker.types import Mount

IMAGE = "gamepulse-spark-bronze:latest"
ML_IMAGE = "gamepulse-ml:latest"
NETWORK = "gamepulse_default"
HOST_PROJECT_DIR = os.environ.get("HOST_PROJECT_DIR", "")

BASE = dict(
    network_mode=NETWORK,
    docker_url="unix://var/run/docker.sock",
    auto_remove="success",
    mount_tmp_dir=False,
)
ENV = {
    "S3_ENDPOINT": "http://minio:9000",
    "LAKEHOUSE_TARGET": "minio",
    "DUCKDB_S3_ENDPOINT": "minio:9000",
    "DUCKDB_PATH": "/warehouse/gamepulse.duckdb",
}
WAREHOUSE = Mount(source=f"{HOST_PROJECT_DIR}/warehouse", target="/warehouse", type="bind")
DUCKDB_EXT = Mount(source="gamepulse_duckdb_ext", target="/root/.duckdb", type="volume")

with DAG(
    dag_id="gamepulse_pipeline",
    description="Silver (Spark), gold (dbt) y sentimiento de reseñas (modelo) cada hora",
    schedule="20 * * * *",  # minuto 20: después del batch horario de Steam (minuto ~9)
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=5)},
    tags=["gamepulse"],
) as dag:
    silver = DockerOperator(
        task_id="silver_spark",
        image=IMAGE,
        command="python -m gamepulse.spark.silver_build --days 2",
        environment=ENV,
        mounts=[Mount(source="gamepulse_spark_ivy", target="/root/.ivy2.5.2", type="volume")],
        **BASE,
    )

    gold = DockerOperator(
        task_id="gold_dbt_build",
        image=IMAGE,
        command="dbt build --profiles-dir .",
        working_dir="/app/dbt",
        environment=ENV,
        mounts=[WAREHOUSE, DUCKDB_EXT],
        **BASE,
    )

    # Clasifica solo las reseñas nuevas (incremental). Tope por ejecución para acotar el tiempo en CPU.
    sentiment = DockerOperator(
        task_id="predict_sentiment",
        image=ML_IMAGE,
        command="python -m gamepulse.ml.predict_sentiment --limit 20000",
        environment={
            "DUCKDB_PATH": "/warehouse/gamepulse.duckdb",
            "SENTIMENT_MODEL_DIR": "/models/sentiment",
        },
        mounts=[
            WAREHOUSE,
            Mount(source=f"{HOST_PROJECT_DIR}/models/sentiment", target="/models/sentiment",
                  type="bind", read_only=True),
        ],
        **BASE,
    )

    # Reconstruye solo los modelos de sentimiento con las predicciones nuevas
    gold_sentiment = DockerOperator(
        task_id="gold_sentiment_dbt",
        image=IMAGE,
        command="dbt build --profiles-dir . --select fct_review_sentiment+ mart_sale_sentiment",
        working_dir="/app/dbt",
        environment=ENV,
        mounts=[WAREHOUSE, DUCKDB_EXT],
        **BASE,
    )

    silver >> gold >> sentiment >> gold_sentiment
