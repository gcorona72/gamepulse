"""Diagrama animado de la arquitectura de GamePulse (estilo neón oscuro).

Genera docs/diagrams/animated/arquitectura.gif (y un PNG estático del primer fotograma).
Uso:  uv run --with matplotlib --with pillow python docs/diagrams/animated/arquitectura_animada.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).parent
FRAMES, FPS = 90, 30

# Paleta (la del ejemplo)
BG = "#0a0c10"
PANEL = "#10141b"
CYAN = "#00d9ff"
GREEN = "#00e27a"
YELLOW = "#ffc857"
PINK = "#ff1a5e"
VIOLET = "#b388ff"
WHITE = "#f5f7fa"
MUTED = "#8b95a5"

fig = plt.figure(figsize=(16, 9), dpi=100)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 160)
ax.set_ylim(0, 90)
ax.axis("off")
ax.set_facecolor(BG)


def zone(x, y, w, h, title, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2",
                                fc="none", ec=color, lw=1.2, ls=(0, (4, 3)), alpha=0.55))
    ax.text(x + w / 2, y + h + 1.6, title, color=color, ha="center", va="bottom",
            fontsize=13, fontweight="bold")


def node(x, y, title, sub, color, w=17, h=8):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0,rounding_size=1.4",
                                fc=PANEL, ec=color, lw=2))
    ax.text(x, y + 1.3, title, color=color, ha="center", va="center", fontsize=11.5,
            fontweight="bold")
    ax.text(x, y - 1.9, sub, color=MUTED, ha="center", va="center", fontsize=8.8)
    return (x, y, w, h)


def store(x, y, title, sub, color, r=5.2):
    """Nodo circular con halo (capas del lakehouse y Kafka)."""
    halo = plt.Circle((x, y), r + 1.2, color=color, alpha=0.12, lw=0)
    ax.add_patch(halo)
    ax.add_patch(plt.Circle((x, y), r, fc=PANEL, ec=color, lw=2.2))
    ax.text(x, y + 0.9, title, color=color, ha="center", va="center", fontsize=11.5,
            fontweight="bold")
    ax.text(x, y - 1.9, sub, color=MUTED, ha="center", va="center", fontsize=8.3)
    return halo


# ---------------- Título ----------------
ax.text(80, 85.5, "GamePulse · Arquitectura del pipeline de datos", color=WHITE,
        ha="center", va="center", fontsize=21, fontweight="bold")
ax.text(80, 81.5, "Twitch + Steam  →  Kafka  →  Spark  →  Lakehouse medallion en Azure  →  IA y consumo",
        color=MUTED, ha="center", va="center", fontsize=11)

# ---------------- Zonas ----------------
zone(3, 14, 23, 58, "1. Fuentes", CYAN)
zone(31, 14, 30, 58, "2. Ingesta · Mac (Docker)", YELLOW)
zone(66, 22, 52, 42, "3. Lakehouse · Azure ADLS Gen2 · Delta", GREEN)
zone(123, 14, 34, 58, "4. Consumo e IA", PINK)

# ---------------- Nodos ----------------
TW = node(14.5, 58, "Twitch API", "audiencia · cada 60 s", CYAN, w=19)
ST = node(14.5, 42, "Steam API", "jugadores · precios · reseñas", CYAN, w=19)
IG = node(14.5, 26, "IGDB API", "cruce Twitch ↔ Steam", CYAN, w=19)

PR = node(46, 58, "Productor", "Python · Twitch", YELLOW, w=18)
SB = node(46, 30, "Extractores", "Python · Steam batch", YELLOW, w=18)
KF_HALO = store(46, 44, "Kafka", "7 días", YELLOW, r=5.3)
ax.text(53.5, 38.2, "Redpanda", color=MUTED, fontsize=8.3, ha="left")
KF = (46, 44)

BR_H = store(76, 43, "BRONZE", "en bruto", "#d9a066")
SI_H = store(92, 43, "SILVER", "PySpark", "#c9d3dd")
GO_H = store(108, 43, "GOLD", "dbt · estrella", YELLOW)
BR, SI, GO = (76, 43), (92, 43), (108, 43)
ax.text(84, 49.5, "limpia", color=MUTED, ha="center", fontsize=8.5)
ax.text(100, 49.5, "modela", color=MUTED, ha="center", fontsize=8.5)

DSH = node(140, 62, "Dashboard", "Streamlit", PINK, w=24)
AGT = node(140, 49, "Agente text-to-SQL", "LLM · Gemini", VIOLET, w=24)
MLM = node(140, 36, "Modelo sentimiento", "Hugging Face · MLflow", VIOLET, w=24)
FAB = node(140, 23, "Fabric + Power BI", "opcional", PINK, w=24)

AF = node(92, 13, "Airflow", "orquesta batch y dbt", GREEN, w=22, h=7)

# ---------------- Aristas ----------------
EDGES = [
    # (puntos del recorrido, color, nº de paquetes)
    ([(24, 58), (37, 58)], CYAN, 3),
    ([(46, 54), (46, 49.3)], YELLOW, 2),
    ([(51.3, 44), (70.8, 43)], YELLOW, 4),
    ([(24, 42), (30, 42), (30, 30), (37, 30)], CYAN, 2),
    ([(24, 26), (31, 26), (37, 28)], CYAN, 1),
    ([(55, 30), (64, 30), (72, 39)], YELLOW, 2),
    ([(81.2, 43), (86.8, 43)], "#d9a066", 2),
    ([(97.2, 43), (102.8, 43)], "#c9d3dd", 2),
    ([(113.2, 45), (120, 62), (128, 62)], YELLOW, 2),
    ([(113.2, 44), (128, 49)], YELLOW, 2),
    ([(113.2, 42), (128, 36)], YELLOW, 2),
    ([(113.2, 41), (120, 23), (128, 23)], PINK, 1),
]
for pts, color, _ in EDGES:
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=1.6, ls=(0, (4, 3)), alpha=0.55)
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4, alpha=0.8,
                                mutation_scale=12))

# Airflow: líneas de orquestación (punteadas)
for (x0, y0), (x1, y1) in [((81, 14), (55, 27)), ((92, 16.5), (92, 37.7)), ((96, 16.5), (106, 37.9))]:
    ax.plot([x0, x1], [y0, y1], color=GREEN, lw=1.2, ls=(0, (1, 3)), alpha=0.7)
ax.text(66, 19.5, "programa", color=GREEN, fontsize=8, alpha=0.8, rotation=24)

# Etiquetas de tecnología en las aristas
ax.text(61, 46, "Spark Structured Streaming", color=YELLOW, fontsize=8.5, ha="center",
        rotation=-3)
ax.text(30.5, 60, "HTTP", color=MUTED, fontsize=8, ha="center")

# ---------------- Animación ----------------
def polyline_point(pts, t):
    seg = np.array(pts, dtype=float)
    lens = np.hypot(*np.diff(seg, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(lens)])
    d = t * cum[-1]
    i = min(np.searchsorted(cum, d, side="right") - 1, len(lens) - 1)
    f = (d - cum[i]) / lens[i] if lens[i] else 0
    return seg[i] + f * (seg[i + 1] - seg[i])


packets = []
for pts, color, n in EDGES:
    for k in range(n):
        glow, = ax.plot([], [], "o", ms=13, color=color, alpha=0.18, mec="none")
        dot, = ax.plot([], [], "o", ms=6.5, color=color, mec=WHITE, mew=0.8)
        packets.append((pts, k / n, glow, dot))

halos = [(KF_HALO, 0.0), (BR_H, 0.2), (SI_H, 0.45), (GO_H, 0.7)]
status = ax.text(80, 5, "", color=MUTED, ha="center", fontsize=10.5)
STAGES = ["captura en tiempo real", "cola duradera en Kafka",
          "bronze: dato en bruto", "silver: limpio y deduplicado",
          "gold: listo para responder preguntas"]


def update(frame):
    t = frame / FRAMES
    artists = []
    for pts, phase, glow, dot in packets:
        x, y = polyline_point(pts, (t + phase) % 1)
        glow.set_data([x], [y])
        dot.set_data([x], [y])
        artists += [glow, dot]
    for halo, ph in halos:
        a = 0.08 + 0.22 * (0.5 + 0.5 * np.sin(2 * np.pi * (t - ph)))
        halo.set_alpha(a)
        artists.append(halo)
    status.set_text("●  " + STAGES[int(t * len(STAGES)) % len(STAGES)])
    artists.append(status)
    return artists


fig.savefig(OUT / "arquitectura.png", facecolor=BG)
anim = FuncAnimation(fig, update, frames=FRAMES, interval=1000 / FPS, blit=True)
anim.save(OUT / "arquitectura.gif", writer=PillowWriter(fps=FPS), savefig_kwargs={"facecolor": BG})
print("OK", OUT / "arquitectura.gif")
