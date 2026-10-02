.PHONY: diagrams install up down reset test lint ingest ingest-stop logs status producer steam bronze inspect bronze-azure inspect-azure game-map steam-store steam-reviews silver silver-full gold gold-docs airflow-logs

install:   ## Instala dependencias de Python
	uv sync --extra spark

up:        ## Levanta Kafka (Redpanda), consola y MinIO
	docker compose up -d

down:      ## Para todo (conserva datos)
	docker compose --profile ingest down

reset:     ## Para y BORRA todos los datos locales
	docker compose --profile ingest down -v

test:
	uv run pytest -q

lint:
	uv run ruff check src tests

ingest:    ## Arranca todo 24/7 en Docker (Twitch + Steam + Spark bronze + Airflow), se reanuda solo
	mkdir -p warehouse
	docker compose --profile ingest up -d --build

ingest-stop: ## Para solo la captura
	docker compose --profile ingest stop twitch-producer steam-players spark-bronze

logs:      ## Ver lo que está haciendo la captura (Ctrl+C para salir)
	docker compose --profile ingest logs -f --tail 50 twitch-producer steam-players spark-bronze

status:    ## Estado de los contenedores
	docker compose --profile ingest ps

producer:  ## (Depuración) productor en primer plano, sin Docker
	uv run python -m gamepulse.ingestion.twitch_producer

steam:     ## Batch: jugadores de Steam -> landing en MinIO
	uv run python -m gamepulse.ingestion.steam_players_batch

steam-store:   ## Batch: precios, descuentos y géneros de Steam -> landing
	uv run python -m gamepulse.ingestion.steam_store_batch

steam-reviews: ## Batch incremental: reseñas nuevas de Steam -> landing
	uv run python -m gamepulse.ingestion.steam_reviews_batch

game-map:  ## Batch: cruce Twitch <-> IGDB <-> Steam -> landing en MinIO
	uv run python -m gamepulse.ingestion.game_map_batch

bronze:    ## (Depuración) Spark bronze en primer plano. Antes: docker compose stop spark-bronze
	uv run python -m gamepulse.spark.twitch_stream_to_bronze

silver:    ## Construye la capa silver (Twitch: últimos 2 días; Steam: completo). Corre en Docker
	docker compose --profile ingest run --build --rm --no-deps spark-bronze python -m gamepulse.spark.silver_build

silver-full: ## Igual que silver, pero reprocesa todo el histórico de Twitch
	docker compose --profile ingest run --build --rm --no-deps spark-bronze python -m gamepulse.spark.silver_build --full

gold:      ## Capa gold con dbt sobre DuckDB: modelos, snapshot SCD2 y tests
	mkdir -p warehouse && cd dbt && uv run --extra gold dbt build --profiles-dir .

gold-docs: ## Documentación y linaje de dbt en http://localhost:8081
	cd dbt && uv run --extra gold dbt docs generate --profiles-dir . && uv run --extra gold dbt docs serve --profiles-dir . --port 8081

airflow-logs: ## Logs de Airflow (UI en http://localhost:8085)
	docker compose --profile ingest logs -f --tail 50 airflow

inspect:   ## Consulta rápida de la tabla bronze
	uv run python -m gamepulse.spark.inspect_bronze

bronze-azure:  ## Igual que bronze, pero escribe en Azure ADLS Gen2
	LAKEHOUSE_TARGET=azure uv run python -m gamepulse.spark.twitch_stream_to_bronze

inspect-azure: ## Consulta la tabla bronze en Azure
	LAKEHOUSE_TARGET=azure uv run python -m gamepulse.spark.inspect_bronze

diagrams:  ## Regenera las imágenes de docs/diagrams (necesita Node.js)
	./scripts/render_diagrams.sh
