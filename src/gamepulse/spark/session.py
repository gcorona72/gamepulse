"""SparkSession con Delta Lake, conector de Kafka y acceso a MinIO (S3A) o ADLS Gen2 (ABFS)."""

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

from gamepulse.config import Settings, get_settings

SPARK_VERSION = "4.0.1"
SCALA_VERSION = "2.13"
EXTRA_PACKAGES = [
    f"org.apache.spark:spark-sql-kafka-0-10_{SCALA_VERSION}:{SPARK_VERSION}",
    "org.apache.hadoop:hadoop-aws:3.4.1",  # misma versión de Hadoop que trae Spark 4.0
]
AZURE_PACKAGES = ["org.apache.hadoop:hadoop-azure:3.4.1"]  # conector ABFS para ADLS Gen2


def build_spark(app_name: str, settings: Settings | None = None) -> SparkSession:
    s = settings or get_settings()
    builder = (
        SparkSession.builder.appName(app_name)
        .master("local[*]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "4")  # en local, pocas particiones
        .config("spark.driver.memory", "4g")
        # S3A -> MinIO
        .config("spark.hadoop.fs.s3a.endpoint", s.s3_endpoint)
        .config("spark.hadoop.fs.s3a.endpoint.region", "us-east-1")
        .config("spark.hadoop.fs.s3a.access.key", s.s3_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", s.s3_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    )
    packages = list(EXTRA_PACKAGES)
    if s.lakehouse_target == "azure":
        if not s.azure_storage_key:
            raise ValueError("Falta AZURE_STORAGE_KEY en .env")
        packages += AZURE_PACKAGES
        # ABFS -> ADLS Gen2 con la clave de la cuenta de almacenamiento
        builder = builder.config(
            f"spark.hadoop.fs.azure.account.key.{s.azure_storage_account}.dfs.core.windows.net",
            s.azure_storage_key,
        )
    spark = configure_spark_with_delta_pip(builder, extra_packages=packages).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
