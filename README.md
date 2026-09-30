# GamePulse

Plataforma de datos *lakehouse* para analítica de videojuegos en tiempo real.
Combina **streaming** (audiencia de Twitch minuto a minuto) y **batch** (jugadores, precios y reseñas de Steam) para responder a una pregunta de negocio:

> **¿Qué impulsa el éxito de un juego?** ¿Un pico de audiencia en Twitch anticipa un pico de jugadores en Steam? ¿Cuánto mueve una rebaja? ¿Qué dicen las reseñas?

## Arquitectura

```
Twitch API ──> Kafka (Redpanda) ──> Spark Structured Streaming ─┐
Steam API ───> extractores batch (Python) ──> landing (JSONL) ──┤
                                                                ▼
                    Lakehouse en Azure Data Lake Storage Gen2 (MinIO en local) · Delta Lake · medallion
                    BRONZE (bruto) → SILVER (PySpark) → GOLD (dbt + DuckDB, modelo en estrella)
                                                                ▼
      Dashboard (Streamlit) · Fabric + Power BI (opcional) · Agente text-to-SQL · Modelo de sentimiento (fine-tuning)

Orquestación: Airflow · Infraestructura: Docker Compose · CI: GitHub Actions
```

| Capa | Tecnología | Estado |
|---|---|---|
| Ingesta streaming | Twitch Helix API → Kafka (Redpanda) | ✅ Semana 1 |
| Ingesta batch | Steam Web API → MinIO (landing) | ✅ Semana 1 (jugadores) |
| Bronze | Spark Structured Streaming → Delta Lake en ADLS Gen2 | ⏳ Semana 2 (MinIO ✅) |
| Silver | PySpark | ⏳ Semana 4 |
| Gold | dbt + DuckDB | ⏳ Semanas 5-6 |
| Orquestación | Airflow | ⏳ Semana 7 |
| Consumo e IA | Streamlit, LLM | ⏳ Semanas 8-9 |

## Puesta en marcha (macOS, Apple Silicon)

```bash
# 1. Herramientas (una vez)
brew install uv openjdk@17
brew install --cask docker          # Docker Desktop: Settings > Resources > Memory ≥ 8 GB
echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 17)' >> ~/.zshrc && source ~/.zshrc

# 2. Proyecto
cp .env.example .env                # rellena TWITCH_CLIENT_ID y TWITCH_CLIENT_SECRET
make install
make test

# 3. Infraestructura
make up
#   Consola de Kafka:  http://localhost:8080
#   Consola de MinIO:  http://localhost:9001  (minioadmin / minioadmin)

# 4. Captura 24/7 (en Docker, se reanuda sola tras reiniciar el Mac)
make ingest        # arranca el productor de Twitch y la captura horaria de Steam
make logs          # ver qué está capturando (Ctrl+C para salir, la captura sigue)
make status        # estado de los contenedores

# 5. Procesamiento (cuando quieras, en una terminal)
make bronze        # Kafka -> Delta bronze (la 1.ª vez descarga conectores de Maven)
make inspect       # comprobar qué hay en bronze
```

## Que la captura sobreviva a reinicios (macOS)

1. Docker Desktop → Settings → General → activar **Start Docker Desktop when you sign in**.
2. Ajustes del Sistema → Batería → Opciones → activar **Evitar la suspensión automática con el adaptador de corriente cuando la pantalla esté apagada**.
3. Tras un reinicio basta con iniciar sesión: Docker arranca y los contenedores (`restart: unless-stopped`) vuelven solos. Los datos viven en volúmenes de Docker y no se pierden; solo falta lo que ocurrió mientras el Mac estaba apagado.

## Estructura

```
Dockerfile                  imagen ligera de los servicios de ingesta
src/gamepulse/
  config.py                 configuración (.env)
  sources/                  clientes de APIs (Twitch, Steam)
  ingestion/                productor Kafka, batch de Steam, contrato de eventos
  spark/                    sesión Spark, esquemas, transformaciones, jobs
  common/                   logging, escritura en S3
config/steam_apps.csv       juegos de Steam seguidos
tests/                      tests unitarios (también de Spark, sin infraestructura)
docs/PLAN.md                plan del TFG semana a semana
```

## Decisiones de diseño

- **Redpanda en lugar de Kafka "clásico"**: misma API de Kafka, un solo contenedor, mucho más ligero en local.
- **Bronze guarda el mensaje en bruto**: si cambia la lógica de silver, se reprocesa sin volver a llamar a las APIs.
- **Checkpoints de Structured Streaming**: garantizan *exactly-once* al reiniciar el job.
- **Transformaciones puras** (`spark/transforms.py`): se prueban con tests unitarios sin Kafka ni MinIO.
- **Contrato de eventos versionado** (`event_version`): permite evolucionar el esquema sin romper consumidores.
