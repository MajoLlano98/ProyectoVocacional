"""Gráficos de la comparación (lee alternativa/resultados/resumen.json)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")
BAYES, RF = "#2a78d6", "#eb6834"                     # paleta validada (CVD ΔE 24.7)
TXT, TXT2, GRID, FONDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def estilo(ax):
    ax.set_facecolor(FONDO)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TXT2, labelsize=10, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def main():
    r = json.load(open(os.path.join(RES, "resumen.json"), encoding="utf-8"))
    b, f = r["realista"]["Red bayesiana"], r["realista"]["Random Forest"]

    # 1 · ¿Cuando dice «90 % seguro», acierta el 90 %?
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200, facecolor=FONDO)
    estilo(ax)
    grupos = ["Interés", "Rendimiento"]
    x = [0, 1]; w = 0.32
    vb = [b["cobertura90_I"] * 100, b["cobertura90_R"] * 100]
    vf = [f["cobertura90_I"] * 100, f["cobertura90_R"] * 100]
    bb = ax.bar([i - w / 2 - 0.01 for i in x], vb, w, color=BAYES, label="Red bayesiana")
    bf = ax.bar([i + w / 2 + 0.01 for i in x], vf, w, color=RF, label="Random Forest")
    for rects, vals in ((bb, vb), (bf, vf)):
        for rc, v in zip(rects, vals):
            ax.text(rc.get_x() + rc.get_width() / 2, v + 1.5, f"{v:.0f} %", ha="center", va="bottom", fontsize=10, color=TXT)
    ax.axhline(90, color=TXT2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(1.62, 90, "lo prometido: 90 %", va="center", ha="right", fontsize=9, color=TXT2, backgroundcolor=FONDO)
    ax.set_xticks(x, grupos, fontsize=11, color=TXT)
    ax.set_ylim(0, 118); ax.set_xlim(-0.6, 1.65); ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("% de casos dentro del rango", color=TXT2, fontsize=10)
    ax.set_title("¿El rango «90 %» contiene el valor real?", loc="left", fontsize=12.5, color=TXT, pad=12)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 1.0), ncol=2, fontsize=9.5, labelcolor=TXT)
    fig.tight_layout(); fig.savefig(os.path.join(RES, "fig1_confianza.png"), facecolor=FONDO); plt.close(fig)

    # 2 · Con pocos estudiantes: error de las probabilidades de zona (Brier; menor es mejor)
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200, facecolor=FONDO)
    estilo(ax)
    curva = r["curva"]
    for mod, col in (("Red bayesiana", BAYES), ("Random Forest", RF)):
        pts = sorted((c["n_entrenamiento"], c["brier"]) for c in curva if c["modelo"] == mod)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(xs, ys, color=col, linewidth=2, marker="o", markersize=7, markeredgecolor=FONDO, markeredgewidth=2)
        ax.text(xs[-1] + 12, ys[-1], mod, color=TXT, fontsize=10, va="center")
        ax.text(xs[0], ys[0] + (0.012 if mod == "Random Forest" else -0.02), f"{ys[0]:.2f}", color=TXT2, fontsize=9, ha="center")
    ax.set_xscale("log"); ax.set_xticks([20, 50, 100, 200, 350], ["20", "50", "100", "200", "350"])
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xlim(16, 620); ax.set_ylim(0.2, 0.43)
    ax.set_xlabel("Estudiantes usados para entrenar", color=TXT2, fontsize=10)
    ax.set_ylabel("Error de Brier (menor = mejor)", color=TXT2, fontsize=10)
    ax.set_title("Calidad de la probabilidad de cada zona según cuántos datos hay", loc="left", fontsize=12.5, color=TXT, pad=12)
    fig.tight_layout(); fig.savefig(os.path.join(RES, "fig2_pocos_datos.png"), facecolor=FONDO); plt.close(fig)
    print("✓ fig1_confianza.png · fig2_pocos_datos.png")


if __name__ == "__main__":
    main()
