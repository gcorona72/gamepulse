"""Dashboard de GamePulse: responde a las 4 preguntas del TFG sobre la capa gold (DuckDB).

Ejecutar:  make dashboard   ->  http://localhost:8501
"""

import os
import time
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

DB_PATH = Path(
    os.environ.get(
        "GAMEPULSE_DUCKDB", Path(__file__).resolve().parents[1] / "warehouse" / "gamepulse.duckdb"
    )
)

st.set_page_config(page_title="GamePulse", page_icon="🎮", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def q(sql: str) -> pd.DataFrame:
    """Consulta de solo lectura. dbt escribe en el mismo fichero cada hora unos segundos:
    si está bloqueado, se reintenta."""
    for attempt in range(6):
        try:
            with duckdb.connect(str(DB_PATH), read_only=True) as con:
                return con.sql(sql).df()
        except duckdb.IOException:
            if attempt == 5:
                raise
            time.sleep(2)
    return pd.DataFrame()


if not DB_PATH.exists():
    st.error(f"No encuentro la base de datos gold en `{DB_PATH}`. Ejecuta `make gold` primero.")
    st.stop()

# ---------------------------------------------------------------- Cabecera y KPIs
st.title("🎮 GamePulse")
st.caption(
    "¿Qué acompaña al éxito de un videojuego? Atención (Twitch), uso (Steam), "
    "satisfacción (reseñas) y palanca comercial (precio)."
)

kpi = q("""
    select
        (select count(*) from gold.dim_game where in_twitch and in_steam) as juegos_cruzados,
        (select count(*) from gold.dim_game) as juegos,
        (select count(distinct hour_ts) from gold.fct_twitch_audience_hourly) as horas,
        (select min(hour_ts) from gold.fct_twitch_audience_hourly) as desde,
        (select count(*) from gold.fct_reviews) as resenas
""").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Juegos en Twitch y Steam (de {int(kpi.juegos)})", int(kpi.juegos_cruzados))
c2.metric(f"Horas de histórico (desde {pd.Timestamp(kpi.desde):%d/%m %H:%M} UTC)", int(kpi.horas))
c3.metric("Reseñas analizadas", f"{int(kpi.resenas):,}".replace(",", "."))
c4.metric("Actualización (Airflow)", "cada hora")

if kpi.horas < 72:
    st.info(
        "Aún hay menos de 3 días de datos: los resultados son preliminares y ganarán "
        "fiabilidad con más semanas de captura."
    )

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "1 · ¿Twitch anticipa a Steam?",
        "2 · Efecto de las rebajas",
        "3 · Se ve vs. se juega",
        "4 · Sentimiento de las reseñas",
    ]
)

# ---------------------------------------------------------------- P1: retraso Twitch -> Steam
with tab1:
    st.subheader("¿Los picos de audiencia en Twitch preceden a los de jugadores en Steam?")
    st.caption(
        "Correlación entre los espectadores en la hora *t* y los jugadores en la hora "
        "*t + retraso*. Si la correlación máxima está en un retraso > 0, Twitch va por delante. "
        "Correlación no implica causalidad."
    )
    lags = q("""
        select game_name, lag_hours as retraso_h, correlation as correlacion, n_hours as n
        from gold.mart_audience_lead
        where correlation is not null
    """)
    if lags.empty:
        st.warning("Todavía no hay horas suficientes para calcular retrasos (mínimo 24 por juego).")
    else:
        best = (
            lags.sort_values("correlacion", ascending=False)
            .groupby("game_name", as_index=False)
            .first()
            .sort_values("correlacion", ascending=False)
        )
        col_a, col_b = st.columns([2, 3])
        with col_a:
            st.markdown("**Mejor retraso por juego**")
            st.dataframe(
                best.rename(
                    columns={
                        "game_name": "Juego",
                        "retraso_h": "Retraso (h)",
                        "correlacion": "Correlación",
                        "n": "Horas",
                    }
                ),
                hide_index=True,
                width="stretch",
                column_config={"Correlación": st.column_config.NumberColumn(format="%.2f")},
            )
            ahead = (best.retraso_h > 0).mean()
            st.metric("Juegos donde Twitch va por delante", f"{ahead:.0%}")
        with col_b:
            game = st.selectbox("Juego", best.game_name.tolist(), key="p1_game")
            chart = (
                alt.Chart(lags[lags.game_name == game])
                .mark_line(point=True)
                .encode(
                    x=alt.X("retraso_h:Q", title="Retraso de Steam respecto a Twitch (horas)"),
                    y=alt.Y("correlacion:Q", title="Correlación", scale=alt.Scale(domain=[-1, 1])),
                    tooltip=["retraso_h", alt.Tooltip("correlacion", format=".2f"), "n"],
                )
            )
            st.altair_chart(chart, width="stretch")
            series = q(f"""
                select hour_ts,
                       avg_viewers / avg(avg_viewers) over () as "Espectadores Twitch",
                       avg_players / avg(avg_players) over () as "Jugadores Steam"
                from gold.mart_twitch_vs_steam_hourly
                where game_name = '{game.replace("'", "''")}' order by hour_ts
            """).melt("hour_ts", var_name="Serie", value_name="Índice")
            st.caption(
                "Evolución horaria normalizada (1 = media del juego) para comparar la forma."
            )
            st.altair_chart(
                alt.Chart(series)
                .mark_line()
                .encode(
                    x=alt.X("hour_ts:T", title=None),
                    y=alt.Y("Índice:Q", title="Índice (media = 1)"),
                    color=alt.Color(
                        "Serie:N",
                        scale=alt.Scale(range=["#9146FF", "#1B9E77"]),
                        legend=alt.Legend(orient="bottom", title=None),
                    ),
                ),
                width="stretch",
            )

# ---------------------------------------------------------------- P2: rebajas
with tab2:
    st.subheader("¿Cuánto aumentan los jugadores durante una rebaja?")
    st.caption(
        "Cada rebaja son días seguidos con descuento. Se compara la media de jugadores durante "
        "la rebaja con la de los 7 días anteriores sin descuento."
    )
    uplift = q("""
        select coalesce(g.game_name, cast(u.appid as varchar)) as juego,
               u.sale_start as inicio, u.sale_end as fin, u.sale_days as dias,
               u.max_discount_percent as descuento,
               u.avg_players_baseline_7d as jugadores_antes,
               u.avg_players_during_sale as jugadores_rebaja,
               u.uplift_pct as variacion
        from gold.mart_sale_uplift as u
        left join gold.dim_game as g on g.game_key = u.game_key
        where u.uplift_pct is not null
        order by u.uplift_pct desc
    """)
    if uplift.empty:
        st.warning(
            "Aún no hay rebajas con 7 días previos de histórico para comparar. "
            "El historial de precios se va construyendo cada día (snapshot SCD2)."
        )
    else:
        m1, m2 = st.columns(2)
        m1.metric("Rebajas analizadas", len(uplift))
        m2.metric("Subida media de jugadores", f"{uplift.variacion.mean():+.1f}%")
        st.altair_chart(
            alt.Chart(uplift)
            .mark_bar()
            .encode(
                x=alt.X("variacion:Q", title="Variación de jugadores durante la rebaja (%)"),
                y=alt.Y("juego:N", sort="-x", title=None),
                color=alt.condition(
                    alt.datum.variacion > 0, alt.value("#1B9E77"), alt.value("#D95F02")
                ),
                tooltip=[
                    "juego",
                    "inicio:T",
                    "fin:T",
                    alt.Tooltip("descuento", title="Descuento %"),
                    alt.Tooltip("variacion", format="+.1f", title="Variación %"),
                ],
            ),
            width="stretch",
        )
        st.dataframe(
            uplift.rename(
                columns={
                    "juego": "Juego",
                    "inicio": "Inicio",
                    "fin": "Fin",
                    "dias": "Días",
                    "descuento": "Descuento %",
                    "jugadores_antes": "Jugadores (7 días antes)",
                    "jugadores_rebaja": "Jugadores (rebaja)",
                    "variacion": "Variación %",
                }
            ),
            hide_index=True,
            width="stretch",
            column_config={"Variación %": st.column_config.NumberColumn(format="%+.1f%%")},
        )
    st.markdown("**Rebajas activas (última captura)**")
    st.dataframe(
        q("""
        select coalesce(g.game_name, cast(p.appid as varchar)) as Juego,
               p.discount_percent as "Descuento %", p.initial_price_eur as "Precio €",
               p.final_price_eur as "Precio rebajado €"
        from gold.fct_steam_price_daily as p
        left join gold.dim_game as g on g.game_key = p.game_key
        where p.on_sale and p.date_day = (select max(date_day) from gold.fct_steam_price_daily)
        order by 2 desc
    """),
        hide_index=True,
        width="stretch",
    )

# ---------------------------------------------------------------- P3: se ve vs se juega
with tab3:
    st.subheader("¿Qué juegos se ven mucho pero se juegan poco (y al revés)?")
    st.caption(
        "Ratio = espectadores medios en Twitch / jugadores medios en Steam. "
        "> 1: se ve más de lo que se juega. Steam solo mide PC."
    )
    ratio = q("""
        select game_name as juego,
               avg(avg_viewers) as espectadores,
               avg(avg_players) as jugadores,
               avg(avg_viewers) / nullif(avg(avg_players), 0) as ratio,
               count(*) as horas
        from gold.mart_twitch_vs_steam_hourly
        group by 1 having avg(avg_players) > 0
    """)
    if ratio.empty:
        st.warning("Sin datos cruzados todavía.")
    else:
        ratio["tipo"] = ratio.ratio.apply(lambda r: "Se ve más" if r > 1 else "Se juega más")
        scatter = (
            alt.Chart(ratio)
            .mark_circle(size=90, opacity=0.8)
            .encode(
                x=alt.X(
                    "jugadores:Q",
                    scale=alt.Scale(type="log"),
                    title="Jugadores medios en Steam (log)",
                ),
                y=alt.Y(
                    "espectadores:Q",
                    scale=alt.Scale(type="log"),
                    title="Espectadores medios en Twitch (log)",
                ),
                color=alt.Color("tipo:N", title=None, legend=alt.Legend(orient="bottom")),
                tooltip=[
                    "juego",
                    alt.Tooltip("espectadores", format=",.0f"),
                    alt.Tooltip("jugadores", format=",.0f"),
                    alt.Tooltip("ratio", format=".2f"),
                ],
            )
        )
        st.altair_chart(scatter, width="stretch")
        a, b = st.columns(2)
        fmt = {
            "ratio": st.column_config.NumberColumn(format="%.2f"),
            "espectadores": st.column_config.NumberColumn(format="%d"),
            "jugadores": st.column_config.NumberColumn(format="%d"),
        }
        a.markdown("**Se ven más de lo que se juegan**")
        a.dataframe(
            ratio.nlargest(10, "ratio")[["juego", "espectadores", "jugadores", "ratio"]],
            hide_index=True,
            width="stretch",
            column_config=fmt,
        )
        b.markdown("**Se juegan más de lo que se ven**")
        b.dataframe(
            ratio.nsmallest(10, "ratio")[["juego", "espectadores", "jugadores", "ratio"]],
            hide_index=True,
            width="stretch",
            column_config=fmt,
        )

# ---------------------------------------------------------------- P4: sentimiento
with tab4:
    st.subheader("¿Cómo evoluciona el sentimiento de las reseñas?")
    st.caption(
        "Hoy: % de reseñas que recomiendan el juego (voted_up). En la semana 9 se añade el "
        "sentimiento estimado por el modelo Transformer entrenado con estas mismas reseñas."
    )
    summary = q("""
        select coalesce(g.game_name, cast(r.appid as varchar)) as juego,
               count(*) as resenas, avg(cast(r.voted_up as int)) as positivas
        from gold.fct_reviews as r
        left join gold.dim_game as g on g.game_key = r.game_key
        group by 1 having count(*) >= 20 order by resenas desc
    """)
    if summary.empty:
        st.warning("Sin reseñas todavía.")
    else:
        a, b = st.columns([2, 3])
        a.dataframe(
            summary,
            hide_index=True,
            width="stretch",
            column_config={
                "positivas": st.column_config.ProgressColumn(
                    "% positivas", format="percent", min_value=0, max_value=1
                )
            },
        )
        game = b.selectbox("Juego", summary.juego.tolist(), key="p4_game")
        daily = q(f"""
            select r.date_day as dia, avg(cast(r.voted_up as int)) as positivas, count(*) as resenas
            from gold.fct_reviews as r
            left join gold.dim_game as g on g.game_key = r.game_key
            where coalesce(g.game_name, cast(r.appid as varchar)) = '{game.replace("'", "''")}'
            group by 1 having count(*) >= 5 order by 1
        """)
        b.altair_chart(
            alt.Chart(daily)
            .mark_line(point=True)
            .encode(
                x=alt.X("dia:T", title=None),
                y=alt.Y(
                    "positivas:Q",
                    title="% positivas",
                    axis=alt.Axis(format="%"),
                    scale=alt.Scale(domain=[0, 1]),
                ),
                tooltip=["dia:T", alt.Tooltip("positivas", format=".0%"), "resenas"],
            ),
            width="stretch",
        )

st.divider()
st.caption(
    "Fuentes: Twitch Helix API, Steam Web API, IGDB · Pipeline: Kafka → Spark (bronze, silver) → "
    "dbt + DuckDB (gold) · Orquestación: Airflow"
)