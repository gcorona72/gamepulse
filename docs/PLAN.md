# Plan del TFG — GamePulse

Entrega: diciembre de 2026 · 10 semanas · La memoria se escribe **cada semana** (un apartado por fase), no al final.

**Regla de recorte:** cada fase funciona por sí sola. Si vas con retraso, se recorta en este orden: 1) Fabric + Power BI, 2) agente text-to-SQL, 3) modelo de sentimiento, 4) streaming (el batch de Steam + dbt + Airflow ya es un TFG completo).

| Sem. | Fechas | Qué construyes | Qué aprendes antes (lo mínimo) | Hecho cuando… |
|---|---|---|---|---|
| 1 | 28 sep – 4 oct | Entorno: Docker, Redpanda, MinIO. Productor Twitch → Kafka. Batch de jugadores de Steam | Docker Compose básico · Kafka: topic, partición, offset, consumer group | Ves mensajes en la consola de Kafka y ficheros en MinIO |
| 2 | 5 – 11 oct | Cuenta de Azure for Students y cuenta de almacenamiento ADLS Gen2. Spark Structured Streaming Kafka → Delta bronze en ADLS (MinIO como alternativa local). Tabla de correspondencia Twitch ↔ Steam vía IGDB (`igdb_id`) | Spark: DataFrames, lazy evaluation, jobs · Structured Streaming: triggers y checkpoints · Delta Lake: transaction log, time travel · ADLS Gen2: cuentas de almacenamiento, contenedores, acceso desde Spark (`abfss://`) | `make inspect` muestra filas en bronze tras reiniciar el job sin duplicados |
| 3 | 12 – 18 oct | Batch de Steam: ficha de tienda (precio, descuento, géneros) y reseñas → bronze | Paginación con cursor · rate limits · idempotencia en cargas batch | Bronze con 20 juegos: precios diarios y ≥50k reseñas |
| 4 | 19 – 25 oct | Silver con PySpark: parseo, tipado, deduplicado, watermarks, agregados por minuto/hora | Watermarks y ventanas · `MERGE` en Delta · calidad de datos | Tablas silver limpias y deduplicadas, con tests |
| 5 | 26 oct – 1 nov | Gold con dbt sobre DuckDB: staging, dimensiones y hechos | Modelado dimensional (Kimball): hechos, dimensiones, granularidad · dbt: models, sources, ref | `dbt build` genera el modelo en estrella |
| 6 | 2 – 8 nov | dbt: tests, snapshots (SCD2 de precios), documentación | SCD tipo 2 · tests genéricos y singulares · `dbt docs` | `dbt build` en verde y linaje documentado |
| 7 | 9 – 15 nov | Airflow: DAGs horarios/diarios de batch + dbt; supervisión del streaming | Airflow: DAG, operadores, schedule, reintentos, backfill | Pipeline completo ejecutándose solo |
| 8 | 16 – 22 nov | Dashboard en Streamlit + CI completa. **Extra opcional:** shortcut de la capa gold de ADLS en Microsoft Fabric (prueba gratuita) + informe de Power BI | Fabric: lakehouse, OneLake shortcuts | Dashboard respondiendo a la pregunta de negocio |
| 9 | 23 – 29 nov | Fine-tuning de un Transformer multilingüe (Hugging Face) con las reseñas etiquetadas por `voted_up`; experimentos registrados en MLflow; predicciones a `fct_reviews`. Agente text-to-SQL (LLM) sobre gold | Fine-tuning con `Trainer` · métricas (accuracy, F1) · MLflow: tracking de experimentos y registro de modelos · text-to-SQL con el esquema como contexto | Modelo evaluado en test y demo: pregunta en lenguaje natural → SQL → respuesta |
| 10 | 30 nov – dic | Cierre de la memoria, demo grabada, ensayo de la defensa | — | Entregado |

## Modelo en estrella (gold, previsto)

- **Hechos:** `fct_twitch_audience_hourly` (juego × hora), `fct_steam_players_hourly`, `fct_steam_price_daily`, `fct_reviews`
- **Dimensiones:** `dim_game` (unifica Twitch, Steam e IGDB), `dim_date`, `dim_time`, `dim_language`
- **SCD2:** historial de precios y descuentos con snapshots de dbt

## Preguntas que debe responder el dashboard

1. ¿Los picos de audiencia en Twitch preceden a los picos de jugadores en Steam? ¿Con cuánto retraso?
2. ¿Cuánto aumentan los jugadores durante una rebaja?
3. ¿Qué juegos tienen mucha audiencia en Twitch pero pocos jugadores (y al revés)?
4. ¿Cómo evoluciona el sentimiento de las reseñas tras una actualización o una rebaja?

## Nube

- **Procesamiento en local** (Mac): Kafka, Spark, dbt, Airflow. **Datos en Azure**: bronze, silver y gold en ADLS Gen2 (Delta), con el crédito de Azure for Students.
- MinIO se mantiene como destino local para trabajar sin conexión (se elige por configuración).

## Riesgos conocidos

- **Correspondencia Twitch ↔ Steam:** Twitch da `igdb_id`; IGDB (misma cuenta de desarrollador de Twitch) relaciona juegos con su `appid` de Steam. Verificar el endpoint en la semana 2.
- **Rate limits de la tienda de Steam:** peticiones espaciadas y reintentos; por eso son batch diarios.
- **Recursos del Mac:** Docker Desktop con ≥ 8 GB; Airflow se añade en la semana 7, no antes.
- **Histórico:** el productor de Twitch debe estar capturando datos cuanto antes; más semanas de datos = mejor análisis en la defensa.
- **Crédito de Azure:** vigilar el consumo en el portal; el almacenamiento de unas decenas de GB cuesta poco, pero las transacciones de muchos ficheros pequeños suman (compactar con `OPTIMIZE` de Delta).
