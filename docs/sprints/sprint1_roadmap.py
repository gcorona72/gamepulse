"""Hoja de ruta visual del Sprint 1 (estilo neón). Genera docs/sprints/sprint1_roadmap.png
Uso:  uv run --with matplotlib python docs/sprints/sprint1_roadmap.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BG, PANEL, WHITE, MUTED = "#0a0c10", "#10141b", "#f5f7fa", "#8b95a5"
CYAN, GREEN, YELLOW, PINK, VIOLET, ORANGE = (
    "#00d9ff", "#00e27a", "#ffc857", "#ff1a5e", "#b388ff", "#ff9f43")

PHASES = [
    ("A · Preparar el Mac", "Semana 1 · día 1", CYAN, [
        ("Instalar herramientas", "brew · uv · Java 21 · Docker"),
        ("Clonar el repo y probar", "make install · make test"),
    ]),
    ("B · Levantar infraestructura", "Semana 1 · día 2", YELLOW, [
        ("Arrancar los servicios", "make up · :8080 · :9001"),
        ("Ajustes del Mac", "autoarranque · sin suspensión"),
    ]),
    ("C · Capturar datos", "Semana 1 · días 2-3", GREEN, [
        ("Credenciales de Twitch", "app en dev.twitch.tv → .env"),
        ("Arrancar la captura", "make ingest · make logs"),
        ("Probar un reinicio", "la captura debe volver sola"),
    ]),
    ("D · Aprender (en paralelo)", "Semana 1 · días 1-5", VIOLET, [
        ("Docker Compose", "servicios · volúmenes · puertos"),
        ("Conceptos de Kafka", "topic · partición · offset · grupo"),
        ("Coursera", "Lagos de datos en AWS"),
    ]),
    ("E · Spark y Azure", "Semana 2", ORANGE, [
        ("Azure for Students", "almacenamiento ADLS Gen2"),
        ("Aprender Spark", "DataFrames · Streaming · Delta"),
        ("Bronze en local", "make bronze → make inspect"),
        ("Bronze en Azure", "Spark escribe en ADLS"),
        ("Cruce Twitch ↔ Steam", "tabla de juegos vía IGDB"),
    ]),
    ("F · Cerrar el sprint", "Semana 2 · último día", PINK, [
        ("Memoria", "introducción y objetivos"),
        ("Retrospectiva + CV", "qué funcionó · añadir al CV"),
    ]),
]

fig = plt.figure(figsize=(18, 10), dpi=110)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 180)
ax.set_ylim(0, 100)
ax.axis("off")

ax.text(90, 94, "GamePulse · Sprint 1 — Ingesta", color=WHITE, ha="center",
        fontsize=24, fontweight="bold")
ax.text(90, 89.3, "28 sep – 11 oct · Objetivo: datos de Twitch y Steam llegando a bronze "
        "y sobreviviendo a un reinicio", color=MUTED, ha="center", fontsize=12)

col_w, gap, x0 = 26.4, 2.3, 4.5
card_h, card_gap, top = 8.2, 2.4, 76
step = 1
prev_anchor = None
for i, (title, when, color, tasks) in enumerate(PHASES):
    x = x0 + i * (col_w + gap)
    cx = x + col_w / 2
    # Cabecera de fase
    ax.add_patch(FancyBboxPatch((x, 80), col_w, 5.4, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=color, ec="none", alpha=0.16))
    ax.text(cx, 83.6, title, color=color, ha="center", va="center", fontsize=11.5,
            fontweight="bold")
    ax.text(cx, 81.3, when, color=MUTED, ha="center", va="center", fontsize=9)
    # Columna punteada
    ax.plot([cx, cx], [top + 1, top - len(tasks) * (card_h + card_gap) + card_gap + 1],
            color=color, lw=1.2, ls=(0, (3, 3)), alpha=0.35, zorder=0)
    for j, (t, sub) in enumerate(tasks):
        y = top - j * (card_h + card_gap) - card_h
        ax.add_patch(FancyBboxPatch((x, y), col_w, card_h,
                                    boxstyle="round,pad=0,rounding_size=1.2",
                                    fc=PANEL, ec=color, lw=1.8))
        # Número del paso
        ax.add_patch(plt.Circle((x + 3.4, y + card_h / 2), 2.3, fc=color, ec="none"))
        ax.text(x + 3.4, y + card_h / 2, str(step), color=BG, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.text(x + 7, y + card_h / 2 + 1.4, t, color=WHITE, ha="left", va="center",
                fontsize=10.5, fontweight="bold")
        ax.text(x + 7, y + card_h / 2 - 1.7, sub, color=MUTED, ha="left", va="center",
                fontsize=8.4)
        if step == 1:
            ax.annotate("EMPIEZA AQUÍ", xy=(x + 1.5, y + card_h + 0.3),
                        xytext=(x + 1.5, y + card_h + 3.2), color=CYAN, fontsize=9,
                        fontweight="bold", ha="left",
                        arrowprops=dict(arrowstyle="-|>", color=CYAN, lw=1.5))
        step += 1
    # Flecha entre fases (la D va en paralelo: línea punteada)
    if i < len(PHASES) - 1:
        ay = 74
        ax.annotate("", xy=(x + col_w + gap - 0.3, ay), xytext=(x + col_w + 0.3, ay),
                    arrowprops=dict(arrowstyle="-|>", color=WHITE, lw=1.4, alpha=0.7))

# Leyenda de "hecho cuando"
ax.add_patch(FancyBboxPatch((4.5, 4), 171, 9, boxstyle="round,pad=0,rounding_size=1.5",
                            fc=PANEL, ec=GREEN, lw=1.5, ls=(0, (4, 3))))
ax.text(8, 10.2, "✔  Sprint terminado cuando…", color=GREEN, fontsize=12, fontweight="bold",
        va="center")
ax.text(8, 6.4, "ves mensajes de Twitch en la consola de Kafka  ·  make inspect muestra filas en "
        "bronze  ·  tras reiniciar el Mac la captura sigue sin duplicados", color=WHITE,
        fontsize=10.5, va="center")
ax.text(175, 17, "Los pasos 8-10 (fase D) se hacen en paralelo a las fases A-C.", color=VIOLET,
        fontsize=9.5, ha="right", style="italic")

out = Path(__file__).with_suffix(".png")
fig.savefig(out, facecolor=BG)
print("OK", out)
