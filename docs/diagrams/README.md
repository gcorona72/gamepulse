# Diagramas de GamePulse

Los diagramas están escritos en **Mermaid** (código en `src/`). GitHub los dibuja directamente en esta página; las versiones en imagen para la memoria y las diapositivas están en `svg/` (vectorial, recomendada) y `png/`.

Para regenerar las imágenes tras editar un `.mmd`:

```bash
make diagrams
```

## Arquitectura animada

![Arquitectura animada](animated/arquitectura.gif)

Generada con matplotlib (`animated/arquitectura_animada.py`). Para regenerarla:

```bash
uv run --with matplotlib --with pillow python docs/diagrams/animated/arquitectura_animada.py
```

## Índice

- [Arquitectura general](#arquitectura-general)
- [Flujo por capas (medallion)](#flujo-por-capas-medallion)
- [Modelo en estrella (gold)](#modelo-en-estrella-gold)
- [Secuencia de la ingesta en streaming](#secuencia-de-la-ingesta-en-streaming)
- [Despliegue](#despliegue)
- [Las dos piezas de IA](#las-dos-piezas-de-ia)
- [Roadmap por sprints](#roadmap-por-sprints)

## Arquitectura general

Componentes del sistema y dónde vive cada uno: fuentes, ingesta en el Mac, lakehouse en Azure y consumo.

```mermaid
%% GamePulse — Arquitectura general
flowchart LR
  subgraph F["① Fuentes"]
    direction TB
    TW["Twitch API<br/>audiencia en directo"]
    ST["Steam API<br/>jugadores · precios · reseñas"]
    IG["IGDB API<br/>cruce Twitch ↔ Steam"]
  end

  subgraph I["② Ingesta · Mac (Docker)"]
    direction TB
    PR["Productor Twitch<br/>Python · cada 60 s"]
    KF[("Kafka · Redpanda<br/>retención 7 días")]
    SB["Extractores Steam<br/>Python · batch"]
    PR --> KF
  end

  subgraph L["③ Lakehouse · Azure ADLS Gen2 · Delta Lake<br/>(MinIO como copia local)"]
    direction TB
    BR[("BRONZE<br/>en bruto")]
    SI[("SILVER<br/>limpio")]
    GO[("GOLD<br/>modelo en estrella")]
    BR -->|PySpark| SI
    SI -->|dbt| GO
  end

  subgraph C["④ Consumo"]
    direction TB
    DSH["Dashboard<br/>Streamlit"]
    AG["Agente text-to-SQL<br/>Gemini"]
    ML["Modelo de sentimiento<br/>Hugging Face · MLflow"]
    FB["Fabric + Power BI<br/>opcional"]
  end

  AF{{"Airflow · orquesta los procesos batch y dbt"}}

  TW --> PR
  ST --> SB
  IG -.-> SB
  KF -->|Spark Streaming| BR
  SB --> BR
  GO --> DSH
  GO --> AG
  GO <--> ML
  GO -.-> FB
  AF -.-> L

  classDef ext fill:#eef2ff,stroke:#6366f1,color:#1e1b4b
  classDef store fill:#ecfdf5,stroke:#10b981,color:#064e3b
  classDef proc fill:#fff7ed,stroke:#f97316,color:#431407
  classDef ai fill:#fdf4ff,stroke:#c026d3,color:#4a044e
  class TW,ST,IG ext
  class KF,BR,SI,GO store
  class PR,SB,AF proc
  class DSH,AG,ML,FB ai
```

Imagen: [`svg/01_arquitectura.svg`](svg/01_arquitectura.svg) · [`png/01_arquitectura.png`](png/01_arquitectura.png)

## Flujo por capas (medallion)

Qué contiene cada capa y qué transformación la produce: bronze (bruto), silver (limpio, PySpark) y gold (negocio, dbt).

```mermaid
%% GamePulse — Flujo de datos por capas (arquitectura medallion)
flowchart TB
  subgraph BRONZE["BRONZE · tal cual llega"]
    B1["twitch_streams<br/>mensaje JSON en bruto + metadatos Kafka"]
    B2["steam_players · steam_store · steam_reviews<br/>JSON en bruto"]
  end
  subgraph SILVER["SILVER · limpio y tipado (PySpark)"]
    S1["twitch_streams<br/>tipos, deduplicado por event_id,<br/>valores imposibles saneados"]
    S2["twitch_audience_minute<br/>agregado juego × minuto"]
    S3["steam_players · steam_prices · steam_reviews<br/>limpios y deduplicados"]
    S4["game_mapping<br/>Twitch ↔ IGDB ↔ Steam"]
  end
  subgraph GOLD["GOLD · modelo de negocio (dbt)"]
    G1["Modelo en estrella<br/>hechos + dimensiones"]
    G2["SCD2 de precios<br/>snapshots de dbt"]
    G3["Tests de calidad<br/>not_null, unique, relationships"]
  end
  B1 --> S1 --> S2
  B2 --> S3
  S4
  S2 --> G1
  S3 --> G1
  S4 --> G1
  S3 --> G2
  G1 --- G3
  classDef b fill:#f5ebe0,stroke:#a47148,color:#3d2b1f
  classDef s fill:#eef1f4,stroke:#8a99a8,color:#1f2933
  classDef g fill:#fef6d8,stroke:#caa53d,color:#3d3000
  class B1,B2 b
  class S1,S2,S3,S4 s
  class G1,G2,G3 g
```

Imagen: [`svg/02_medallion.svg`](svg/02_medallion.svg) · [`png/02_medallion.png`](png/02_medallion.png)

## Modelo en estrella (gold)

Hechos y dimensiones de la capa gold, más el historial SCD2 de precios.

```mermaid
%% GamePulse — Modelo dimensional de la capa gold (previsto)
erDiagram
  DIM_GAME ||--o{ FCT_TWITCH_AUDIENCE_HOURLY : ""
  DIM_GAME ||--o{ FCT_STEAM_PLAYERS_HOURLY : ""
  DIM_GAME ||--o{ FCT_STEAM_PRICE_DAILY : ""
  DIM_GAME ||--o{ FCT_REVIEWS : ""
  DIM_DATE ||--o{ FCT_TWITCH_AUDIENCE_HOURLY : ""
  DIM_DATE ||--o{ FCT_STEAM_PLAYERS_HOURLY : ""
  DIM_DATE ||--o{ FCT_STEAM_PRICE_DAILY : ""
  DIM_DATE ||--o{ FCT_REVIEWS : ""
  DIM_TIME ||--o{ FCT_TWITCH_AUDIENCE_HOURLY : ""
  DIM_TIME ||--o{ FCT_STEAM_PLAYERS_HOURLY : ""
  DIM_LANGUAGE ||--o{ FCT_REVIEWS : ""
  DIM_GAME ||--o{ SNP_GAME_PRICE : "historial SCD2"

  DIM_GAME {
    int game_key PK
    string twitch_game_id
    string igdb_id
    int steam_appid
    string game_name
    string genres
    date release_date
  }
  DIM_DATE {
    int date_key PK
    date full_date
    int year
    int month
    int day_of_week
    boolean is_weekend
  }
  DIM_TIME {
    int time_key PK
    int hour
  }
  DIM_LANGUAGE {
    int language_key PK
    string language_code
  }
  FCT_TWITCH_AUDIENCE_HOURLY {
    int game_key FK
    int date_key FK
    int time_key FK
    bigint avg_viewers
    bigint peak_viewers
    int live_streams
  }
  FCT_STEAM_PLAYERS_HOURLY {
    int game_key FK
    int date_key FK
    int time_key FK
    bigint avg_players
    bigint peak_players
  }
  FCT_STEAM_PRICE_DAILY {
    int game_key FK
    int date_key FK
    decimal price_eur
    int discount_pct
    boolean is_on_sale
  }
  FCT_REVIEWS {
    string review_id PK
    int game_key FK
    int date_key FK
    int language_key FK
    boolean voted_up
    string sentiment_label
    float sentiment_score
    float playtime_hours
  }
  SNP_GAME_PRICE {
    int game_key FK
    decimal price_eur
    int discount_pct
    timestamp valid_from
    timestamp valid_to
  }
```

Imagen: [`svg/03_modelo_estrella.svg`](svg/03_modelo_estrella.svg) · [`png/03_modelo_estrella.png`](png/03_modelo_estrella.png)

## Secuencia de la ingesta en streaming

Cómo viaja un dato de Twitch hasta bronze y cómo se garantiza que no se pierde ni se duplica.

```mermaid
%% GamePulse — Secuencia de la ingesta en streaming (Twitch)
sequenceDiagram
  autonumber
  participant P as Productor Twitch
  participant T as Twitch API
  participant K as Kafka (Redpanda)
  participant S as Spark Streaming
  participant L as ADLS Gen2 (bronze)

  loop cada 60 segundos
    P->>T: token OAuth (client credentials, si ha caducado)
    P->>T: GET /games/top (50 juegos)
    loop por cada juego
      P->>T: GET /streams?game_id=… (hasta 100 directos)
      T-->>P: directos con espectadores
    end
    P->>K: publica un evento por directo (clave = game_id)
  end

  loop micro-lote cada 1 minuto
    S->>K: lee desde el último offset guardado
    K-->>S: eventos nuevos
    S->>L: append en tabla Delta (partición event_date)
    S->>L: guarda checkpoint (offsets procesados)
  end

  Note over K,L: Si Spark se para, Kafka conserva los mensajes 7 días.<br/>Al reiniciar, el checkpoint evita duplicados (exactly-once).
```

Imagen: [`svg/04_secuencia_ingesta.svg`](svg/04_secuencia_ingesta.svg) · [`png/04_secuencia_ingesta.png`](png/04_secuencia_ingesta.png)

## Despliegue

Contenedores, procesos locales, servicios de Azure y servicios externos.

```mermaid
%% GamePulse — Despliegue (dónde corre cada pieza)
flowchart LR
  subgraph MAC["MacBook Pro M3 Pro · Docker Desktop"]
    direction TB
    subgraph ING["Contenedores de ingesta<br/>(profile: ingest)"]
      TP["twitch-producer"]
      SPL["steam-players"]
    end
    subgraph INFRA["Contenedores de infraestructura<br/>(restart: unless-stopped)"]
      RP["redpanda · :19092"]
      RC["console · :8080"]
      MI["minio · :9000/:9001"]
    end
    subgraph LOC["Procesos locales<br/>(uv · Python 3.12 · Java 21)"]
      SJ["Spark"]
      DB["dbt"]
      AFW["Airflow"]
      STL["Streamlit"]
    end
    ING --> INFRA
    LOC -->|lee Kafka| INFRA
  end

  subgraph AZURE["Azure for Students"]
    direction TB
    ST[("ADLS Gen2<br/>Delta Lake")]
    FAB["Fabric + Power BI<br/>(opcional)"]
    ST -.-> FAB
  end

  subgraph EXT["Servicios externos"]
    direction TB
    GH["GitHub<br/>repo + Actions (CI)"]
    HF["Hugging Face Hub"]
    GM["Gemini API"]
  end

  LOC -->|lee y escribe| ST
  LOC -.-> EXT
```

Imagen: [`svg/05_despliegue.svg`](svg/05_despliegue.svg) · [`png/05_despliegue.png`](png/05_despliegue.png)

## Las dos piezas de IA

El modelo de sentimiento que se entrena (fine-tuning) y el agente text-to-SQL que usa un LLM por API.

```mermaid
%% GamePulse — Las dos piezas de IA
flowchart LR
  subgraph FT["Modelo de sentimiento · se ENTRENA"]
    R[("Reseñas Steam<br/>silver")] --> DS["Dataset etiquetado<br/>voted_up = sí/no"]
    DS --> SPLIT["train / validación / test"]
    BASE["xlm-roberta-base<br/>Hugging Face Hub"] --> TR
    SPLIT --> TR["Fine-tuning<br/>transformers · Trainer"]
    TR --> EV["Evaluación<br/>accuracy · F1"]
    TR -.registra.-> MLF[("MLflow<br/>experimentos y modelos")]
    EV --> PRED["Predicciones"] --> FR[("gold.fct_reviews<br/>sentiment_label")]
  end
  subgraph AGT["Agente text-to-SQL · NO se entrena"]
    Q["Pregunta en español"] --> LLM["LLM por API<br/>Gemini"]
    SCH["Esquema de gold<br/>como contexto"] --> LLM
    LLM --> SQL["SQL generado"] --> EXE["DuckDB ejecuta"] --> ANS["Respuesta en español"]
    EXE -.error.-> LLM
  end
  FR -.-> SCH
```

Imagen: [`svg/06_pipeline_ia.svg`](svg/06_pipeline_ia.svg) · [`png/06_pipeline_ia.png`](png/06_pipeline_ia.png)

## Roadmap por sprints

Planificación del TFG en 5 sprints de 2 semanas.

```mermaid
%% GamePulse — Roadmap del TFG por sprints
gantt
  title GamePulse · Roadmap (5 sprints de 2 semanas)
  dateFormat YYYY-MM-DD
  axisFormat %d %b
  todayMarker off
  section Sprint 1 · Ingesta
  Entorno, Kafka, productores           :s1a, 2026-09-28, 7d
  Spark → bronze en ADLS + cruce IGDB   :s1b, after s1a, 7d
  section Sprint 2 · Fuentes y limpieza
  Precios, descuentos y reseñas Steam   :s2a, 2026-10-12, 7d
  Capa silver con PySpark               :s2b, after s2a, 7d
  section Sprint 3 · Modelo de negocio
  Gold con dbt (estrella)               :s3a, 2026-10-26, 7d
  Tests, SCD2 y documentación           :s3b, after s3a, 7d
  section Sprint 4 · Orquestación y consumo
  Airflow                               :s4a, 2026-11-09, 7d
  Dashboard + CI (+ Fabric opcional)    :s4b, after s4a, 7d
  section Sprint 5 · IA y cierre
  Fine-tuning + agente text-to-SQL      :s5a, 2026-11-23, 7d
  Memoria final y defensa               :crit, s5b, after s5a, 10d
```

Imagen: [`svg/07_roadmap.svg`](svg/07_roadmap.svg) · [`png/07_roadmap.png`](png/07_roadmap.png)
