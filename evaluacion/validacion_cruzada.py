"""
Validación cruzada repetida: prototipo v1.0 (baseline) vs v1.1 (ajustado) y Random Forest.

Escenario de la tesis (Módulo 3B): 500 estudiantes con notas reales + CHASIDE simulado con verdad conocida.
Diseño: 3 réplicas de simulación (semillas 2026-2028) × validación cruzada de 5 folds = 15 evaluaciones por modelo,
todas con LOS MISMOS folds para todos los modelos (comparación pareada).

Modelos
  · Bayes v1.0  (baseline): calibración CHASIDE y normas de notas con TODOS los estudiantes; λ y ρ con todo el train;
                umbral de certeza fijo 0,60.
  · Bayes v1.1  (ajustado, sin etiquetas) = A1 + A3:
        A1  sin fuga de información: KR-20, normas CHASIDE y normas de notas solo con el fold de entrenamiento.
        A3  umbral de certeza elegido SIN etiquetas: el menor u tal que la exactitud esperada (media de la
            probabilidad de la zona elegida, que el modelo calcula por sí mismo) sea ≥ 0,90 en el train.
  · Ablaciones: «solo A1» (umbral 0,60) y «A1+A2+A3», con
        A2  aprendizaje robusto: λ y ρ sin aplicaciones con alerta de consistencia o incompletas (descartado:
            sin efecto medible, ver sensibilidad.py).
  · RF base     : 300 árboles, min_samples_leaf=5 (alternativa de la semana anterior).
  · RF ajustado : hiperparámetros por GridSearchCV interno (3 folds) + intervalos conformales (split 80/20).
                  Necesita etiquetas (ventaja que en el colegio no existe).

Uso:  python evaluacion/validacion_cruzada.py          (~3-5 min; escribe evaluacion/resultados/)
"""
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import GridSearchCV, KFold

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ); sys.path.insert(0, os.path.join(RAIZ, "alternativa"))
import comparacion as cmp  # noqa: E402
from modelo import bayes, chaside, configuracion as cfg  # noqa: E402
from modelo.constantes import CODIGOS  # noqa: E402

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
ZONAS = cmp.ZONAS
SEMILLAS = (2026, 2027, 2028)
K = 5
UMBRALES = np.round(np.arange(0.50, 0.851, 0.025), 3)
OBJETIVO_EXACTITUD = 0.90
FECHA = pd.Timestamp('2026-10-01').date()


# ───────────────────────── evidencia con o sin fuga ─────────────────────────
def evidencia(rend, apps, claves, ids_calib):
    """KR-20/normas CHASIDE y normas de notas calculadas solo con ids_calib (todos = v1.0; train = v1.1)."""
    cal = chaside.calibrar([apps[i] for i in ids_calib], claves)
    base = rend[rend['id'].isin(ids_calib)].groupby('area')['R'].agg(['mean', 'std'])
    EV, CRIT = {}, {}
    filas = {(r.id, r.area): (r.R, r.W_efectiva) for r in rend.itertuples()}
    for i, ap in apps.items():
        z, crit, _ = chaside.evidencia(ap["respuestas"], ap, cal, claves, FECHA)
        EV[i] = {}
        for a in CODIGOS:
            R, W = filas.get((i, a), (np.nan, np.nan))
            zn = None if pd.isna(R) else float((R - base.loc[a, 'mean']) / base.loc[a, 'std'])
            EV[i][a] = {"z_int": z[a]["interes"], "z_apt": z[a]["aptitud"], "z_notas": zn,
                        "W_efectiva": None if pd.isna(W) else W}
        CRIT[i] = crit
    return EV, CRIT, cal


def aprender(EV, CRIT, por_anio, train, cal, robusto):
    if robusto:   # A2: fuera las aplicaciones dudosas al estimar λ y ρ
        train = [i for i in train if CRIT[i]["consistencia"] != "alerta" and CRIT[i]["completitud"] != "incompleta"]
    return cmp.bayes_ajustar(EV, por_anio, train, cal)


def aplicar_umbral(pred, u):
    P = pred[[f"P_{k}" for k in ZONAS]]
    pred = pred.copy()
    pred["zona"] = np.where(P.max(axis=1) >= u, P.idxmax(axis=1).str[2:], "indeterminado")
    return pred


def elegir_umbral(pred_train):
    """A3 sin etiquetas: exactitud esperada = media de max P entre las áreas decididas."""
    pmax = pred_train[[f"P_{k}" for k in ZONAS]].max(axis=1).values
    for u in UMBRALES:
        dec = pmax >= u
        if dec.any() and pmax[dec].mean() >= OBJETIVO_EXACTITUD:
            return float(u), float(pmax[dec].mean()), float(1 - dec.mean())
    return float(UMBRALES[-1]), float(pmax[pmax >= UMBRALES[-1]].mean()), float((pmax < UMBRALES[-1]).mean())


# ───────────────────────── Random Forest ajustado ─────────────────────────
GRID = {"min_samples_leaf": [2, 5, 10, 20], "max_features": [1.0, 0.5, "sqrt"]}


def rf_ajustado(EV, CRIT, verdad, train, test, semilla):
    rng = np.random.default_rng(semilla)
    tr = np.array(train); rng.shuffle(tr)
    n_cal = int(0.2 * len(tr)); cal_ids, fit_ids = sorted(tr[:n_cal]), sorted(tr[n_cal:])
    X = cmp.matriz(EV, CRIT, fit_ids)
    yI = np.array([verdad[(r.id, r.area)][0] for r in X.itertuples()])
    yR = np.array([verdad[(r.id, r.area)][1] for r in X.itertuples()])
    yZ = np.array([cmp.zona_de(a, b) for a, b in zip(yI, yR)])
    grupos = X["id"].values
    cv = list(KFold(3, shuffle=True, random_state=semilla).split(np.unique(grupos)))
    uniq = np.unique(grupos)
    cv = [(np.where(np.isin(grupos, uniq[a]))[0], np.where(np.isin(grupos, uniq[b]))[0]) for a, b in cv]  # folds por estudiante
    gs = GridSearchCV(RandomForestRegressor(n_estimators=120, random_state=semilla, n_jobs=-1), GRID,
                      scoring="neg_mean_squared_error", cv=cv).fit(X[cmp.COLS], yI)
    mejor = gs.best_params_
    kw = dict(n_estimators=300, random_state=semilla, n_jobs=-1, **mejor)
    mI = RandomForestRegressor(**kw).fit(X[cmp.COLS], yI)
    mR = RandomForestRegressor(**kw).fit(X[cmp.COLS], yR)
    mZ = RandomForestClassifier(**kw).fit(X[cmp.COLS], yZ)
    # intervalos conformales (split): cuantil 90 % del error absoluto en la parte de calibración
    Xc = cmp.matriz(EV, CRIT, cal_ids)
    rI = np.abs(mI.predict(Xc[cmp.COLS]) - [verdad[(r.id, r.area)][0] for r in Xc.itertuples()])
    rR = np.abs(mR.predict(Xc[cmp.COLS]) - [verdad[(r.id, r.area)][1] for r in Xc.itertuples()])
    n = len(rI); q = min(1.0, math.ceil((n + 1) * 0.9) / n)
    qI, qR = np.quantile(rI, q), np.quantile(rR, q)
    out = cmp.rf_predecir((mI, mR, mZ), EV, CRIT, test)
    out["lo_I"], out["hi_I"] = out.mu_I - qI, out.mu_I + qI
    out["lo_R"], out["hi_R"] = out.mu_R - qR, out.mu_R + qR
    return out, mejor


# ───────────────────────── resumen estadístico ─────────────────────────
METRICAS = ["r_I", "r_R", "RMSE_I", "RMSE_R", "cobertura90_I", "cobertura90_R", "exactitud_zona", "indeterminados",
            "exactitud_zona_todas", "brier", "top1_en_top3", "segundos"]


def ic95(x):
    x = np.asarray(x, float); m = x.mean(); s = x.std(ddof=1); n = len(x)
    h = stats.t.ppf(0.975, n - 1) * s / math.sqrt(n)
    return m, s, m - h, m + h


def main():
    os.makedirs(SALIDA, exist_ok=True)
    claves = cfg.cargar_claves(); fuentes = cfg.cargar_fuentes()
    rend, por_anio = cmp.cargar_notas()
    filas, umbrales, params_rf, curva = [], [], [], []
    t0 = time.time()
    for semilla in SEMILLAS:
        apps, verdad, _ = cmp.simular(rend, por_anio, claves, "realista", semilla=semilla)
        ids = np.array(sorted(apps))
        EV0, CRIT0, cal0 = evidencia(rend, apps, claves, list(ids))           # v1.0: con todos (fuga)
        for f, (a, b) in enumerate(KFold(K, shuffle=True, random_state=7).split(ids)):
            train, test = sorted(ids[a]), sorted(ids[b])
            res = {}
            # ── Bayes v1.0
            t = time.perf_counter()
            P = aprender(EV0, CRIT0, por_anio, train, cal0, robusto=False)
            pb0 = cmp.bayes_predecir(EV0, CRIT0, P, cal0, test, fuentes)
            res["Bayes v1.0"] = (pb0, time.perf_counter() - t)
            # ── Bayes v1.1 (A1 + A3)
            t = time.perf_counter()
            EV1, CRIT1, cal1 = evidencia(rend, apps, claves, train)
            P1 = aprender(EV1, CRIT1, por_anio, train, cal1, robusto=False)
            u, esperada, indet_tr = elegir_umbral(cmp.bayes_predecir(EV1, CRIT1, P1, cal1, train, fuentes))
            pb1_crudo = cmp.bayes_predecir(EV1, CRIT1, P1, cal1, test, fuentes)
            pb1 = aplicar_umbral(pb1_crudo, u)
            res["Bayes v1.1"] = (pb1, time.perf_counter() - t)
            umbrales.append({"semilla": semilla, "fold": f, "umbral": u, "exactitud_esperada": esperada})
            # ── ablaciones (separan el efecto de cada ajuste)
            res["Ablación solo A1"] = (aplicar_umbral(pb1_crudo, 0.60), res["Bayes v1.1"][1])
            P2 = aprender(EV1, CRIT1, por_anio, train, cal1, robusto=True)
            u2, _, _ = elegir_umbral(cmp.bayes_predecir(EV1, CRIT1, P2, cal1, train, fuentes))
            res["Ablación A1+A2+A3"] = (aplicar_umbral(cmp.bayes_predecir(EV1, CRIT1, P2, cal1, test, fuentes), u2), res["Bayes v1.1"][1])
            # ── curva del umbral (las etiquetas se usan SOLO para evaluar, nunca para elegir)
            for uu in UMBRALES:
                m = cmp.metricas(aplicar_umbral(pb1_crudo, uu), verdad)
                curva.append({"semilla": semilla, "fold": f, "umbral": uu, "exactitud_zona": m["exactitud_zona"],
                              "indeterminados": m["indeterminados"]})
            # ── RF base
            t = time.perf_counter()
            prf = cmp.rf_predecir(cmp.rf_ajustar(EV0, CRIT0, verdad, train, semilla=f), EV0, CRIT0, test)
            res["RF base"] = (prf, time.perf_counter() - t)
            # ── RF ajustado
            t = time.perf_counter()
            prf1, mejor = rf_ajustado(EV1, CRIT1, verdad, train, test, semilla=f)
            res["RF ajustado"] = (prf1, time.perf_counter() - t)
            params_rf.append({"semilla": semilla, "fold": f, **mejor})
            for mod, (pred, seg) in res.items():
                filas.append({"semilla": semilla, "fold": f, "modelo": mod, **cmp.metricas(pred, verdad), "segundos": seg})
            print(f"semilla {semilla} fold {f}: umbral v1.1 = {u:.3f} · {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(filas)
    df.to_csv(os.path.join(SALIDA, "metricas_por_fold.csv"), index=False)
    pd.DataFrame(curva).to_csv(os.path.join(SALIDA, "curva_umbral.csv"), index=False)
    pd.DataFrame(umbrales).to_csv(os.path.join(SALIDA, "umbral_por_fold.csv"), index=False)
    pd.DataFrame(params_rf).to_csv(os.path.join(SALIDA, "rf_hiperparametros.csv"), index=False)

    resumen = []
    for mod, g in df.groupby("modelo", sort=False):
        for m in METRICAS:
            mu, sd, lo, hi = ic95(g[m])
            resumen.append({"modelo": mod, "metrica": m, "media": mu, "de": sd, "ic95_inf": lo, "ic95_sup": hi})
    resumen = pd.DataFrame(resumen)
    resumen.to_csv(os.path.join(SALIDA, "resumen_ic95.csv"), index=False)

    # diferencias pareadas (mismos folds)
    pares = [("Bayes v1.1", "Bayes v1.0"), ("Ablación solo A1", "Bayes v1.0"), ("Ablación A1+A2+A3", "Bayes v1.1"),
             ("Bayes v1.1", "RF ajustado"),
             ("Bayes v1.0", "RF base"), ("RF ajustado", "RF base")]
    dif = []
    for a, b in pares:
        A = df[df.modelo == a].set_index(["semilla", "fold"]); B = df[df.modelo == b].set_index(["semilla", "fold"])
        for m in METRICAS[:-1]:
            d = (A[m] - B[m]).values
            mu, sd, lo, hi = ic95(d)
            p = stats.wilcoxon(d).pvalue if np.any(d != 0) else 1.0
            dif.append({"comparacion": f"{a} − {b}", "metrica": m, "dif_media": mu, "ic95_inf": lo, "ic95_sup": hi,
                        "p_wilcoxon": p, "folds_a_favor_de_A": int((d > 0).sum())})
    dif = pd.DataFrame(dif)
    dif.to_csv(os.path.join(SALIDA, "diferencias_pareadas.csv"), index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(resumen.pivot(index="metrica", columns="modelo", values="media").round(3).to_string())
        print(resumen.pivot(index="metrica", columns="modelo", values="de").round(3).to_string())
        print(dif.round(4).to_string(index=False))
        print(pd.DataFrame(umbrales).describe().round(3).to_string())
        print(pd.DataFrame(params_rf).drop(columns=["semilla", "fold"]).value_counts().to_string())


if __name__ == "__main__":
    main()
