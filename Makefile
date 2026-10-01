.PHONY: diagrams install up down reset test lint ingest ingest-stop logs status producer steam bronze inspect bronze-azure inspect-azure game-map

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

ingest:    ## Arranca la captura 24/7 en Docker (Twitch + Steam), se reanuda sola tras reiniciar
	docker compose --profile ingest up -d --build

ingest-stop: ## Para solo la captura
	docker compose --profile ingest stop twitch-producer steam-players

logs:      ## Ver lo que está haciendo la captura (Ctrl+C para salir)
	docker compose --profile ingest logs -f --tail 50 twitch-producer steam-players

status:    ## Estado de los contenedores
	docker compose --profile ingest ps

producer:  ## (Depuración) productor en primer plano, sin Docker
	uv run python -m gamepulse.ingestion.twitch_producer

steam:     ## Batch: jugadores de Steam -> landing en MinIO
	uv run python -m gamepulse.ingestion.steam_players_batch

game-map:  ## Batch: cruce Twitch <-> IGDB <-> Steam -> landing en MinIO
	uv run python -m gamepulse.ingestion.game_map_batch

bronze:    ## Spark Structured Streaming: Kafka -> Delta bronze
	uv run python -m gamepulse.spark.twitch_stream_to_bronze

inspect:   ## Consulta rápida de la tabla bronze
	uv run python -m gamepulse.spark.inspect_bronze

bronze-azure:  ## Igual que bronze, pero escribe en Azure ADLS Gen2
	LAKEHOUSE_TARGET=azure uv run python -m gamepulse.spark.twitch_stream_to_bronze

inspect-azure: ## Consulta la tabla bronze en Azure
	LAKEHOUSE_TARGET=azure uv run python -m gamepulse.spark.inspect_bronze

diagrams:  ## Regenera las imágenes de docs/diagrams (necesita Node.js)
	./scripts/render_diagrams.sh
