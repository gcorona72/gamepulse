# Capa gold (dbt + DuckDB)

Lee las tablas Delta de silver (MinIO) y construye el modelo en estrella en `warehouse/gamepulse.duckdb`.

```bash
make gold        # dbt build: staging -> marts -> snapshot -> tests
make gold-docs   # documentación y linaje en http://localhost:8081
```

| Capa | Modelos |
|---|---|
| staging | `stg_*`: vistas 1:1 sobre silver, solo renombrar y tipar |
| intermediate | `int_twitch_steam_link`: último appid de Steam por juego de Twitch |
| marts (gold) | `dim_game`, `dim_date`, `fct_twitch_audience_hourly`, `fct_steam_players_hourly`, `fct_steam_price_daily`, `fct_reviews`, `mart_twitch_vs_steam_hourly` |
| snapshots | `snap_steam_price`: historial de precios (SCD tipo 2) |
