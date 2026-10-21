"""Figuras del reporte de validación (lee evaluacion/resultados/). Uso: python evaluacion/graficos.py"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
BAYES, RF = "#2a78d6", "#eb6834"
TXT, TXT2, GRID, FONDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def estilo(ax):
    ax.set_facecolor(FONDO)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=TXT2, labelsize=9, length=0)
    ax.grid(True, color=GRID, linewidth=0.7); ax.set_axisbelow(True)


def ic(x):
    x = np.asarray(x, float); h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return x.mean(), h


def main():
    df = pd.read_csv(os.path.join(RES, "metricas_por_fold.csv"))
    curva = pd.read_csv(os.path.join(RES, "curva_umbral.csv"))

    # Fig. 1 · distribución por fold (15 evaluaciones) con media e IC 95 %
    modelos = [("Bayes v1.0", BAYES, "none"), ("Bayes v1.1", BAYES, BAYES), ("RF base", RF, "none"), ("RF ajustado", RF, RF)]
    paneles = [("brier", "Error de Brier de las zonas\n(menor = mejor)"), ("cobertura90_I", "Cobertura del rango 90 %\n(interés; ideal = 0,90)"),
               ("exactitud_zona", "Exactitud de las zonas\nasignadas")]
    fig, axs = plt.subplots(1, 3, figsize=(9.6, 3.3), dpi=200, facecolor=FONDO)
    rng = np.random.default_rng(3)
    for ax, (m, titulo) in zip(axs, paneles):
        estilo(ax)
        for k, (mod, col, relleno) in enumerate(modelos):
            v = df[df.modelo == mod][m].values
            ax.scatter(k + rng.uniform(-0.13, 0.13, len(v)), v, s=14, facecolor=relleno, edgecolor=col, linewidth=1, alpha=0.75, zorder=3)
            mu, h = ic(v)
            ax.errorbar(k + 0.32, mu, yerr=h, fmt="o", color=TXT, markersize=4, capsize=3, linewidth=1.2, zorder=4)
        if m == "cobertura90_I":
            ax.axhline(0.90, color=TXT2, linestyle=(0, (4, 3)), linewidth=1)
        ax.set_xticks(range(4), ["Bayes\nv1.0", "Bayes\nv1.1", "RF\nbase", "RF\najustado"], fontsize=8.5, color=TXT)
        ax.set_title(titulo, fontsize=9.5, color=TXT, loc="left")
        ax.grid(axis="x", visible=False)
    fig.text(0.01, 0.005, "Puntos: cada uno de los 15 folds (3 simulaciones × 5 folds). Negro: media ± IC 95 %. Relleno = modelo ajustado.",
             fontsize=7.5, color=TXT2)
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(os.path.join(RES, "fig_folds.png"), facecolor=FONDO); plt.close(fig)

    # Fig. 2 · compromiso del umbral de certeza
    g = curva.groupby("umbral").agg(e=("exactitud_zona", "mean"), es=("exactitud_zona", "std"),
                                    i=("indeterminados", "mean"), is_=("indeterminados", "std")).reset_index()
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200, facecolor=FONDO)
    estilo(ax)
    ax.plot(g.i * 100, g.e * 100, color=BAYES, linewidth=2, marker="o", markersize=3.5, zorder=3)
    for _, r in g.iterrows():
        ax.plot([r.i * 100] * 2, [(r.e - r.es) * 100, (r.e + r.es) * 100], color=BAYES, alpha=0.35, linewidth=1)
    for u, txt, dx, dy in ((0.60, "v1.0 · umbral 0,60", 1.2, -1.2), (0.675, "v1.1 · umbral 0,675\n(elegido sin etiquetas)", 1.2, -2.2)):
        r = g.loc[(g.umbral - u).abs().idxmin()]
        ax.scatter(r.i * 100, r.e * 100, s=60, facecolor=BAYES if u > 0.6 else "none", edgecolor=TXT, linewidth=1.2, zorder=5)
        ax.annotate(txt, (r.i * 100, r.e * 100), xytext=(r.i * 100 + dx, r.e * 100 + dy), fontsize=8.5, color=TXT)
    ax.axhline(90, color=TXT2, linestyle=(0, (4, 3)), linewidth=1)
    ax.text(g.i.max() * 100, 90.3, "objetivo 90 %", ha="right", fontsize=8, color=TXT2)
    ax.set_xlabel("Áreas que quedan «indeterminado» (%)", fontsize=9, color=TXT2)
    ax.set_ylabel("Zonas asignadas correctas (%)", fontsize=9, color=TXT2)
    ax.set_title("Subir el umbral: más aciertos a cambio de más «indeterminado»", fontsize=10, color=TXT, loc="left")
    fig.text(0.01, 0.01, "Media de 15 folds; líneas verticales: ± 1 desviación estándar entre folds. Las etiquetas solo se usan para evaluar.",
             fontsize=7.5, color=TXT2)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(os.path.join(RES, "fig_umbral.png"), facecolor=FONDO); plt.close(fig)
    print("✓ fig_folds.png · fig_umbral.png")


if __name__ == "__main__":
    main()
