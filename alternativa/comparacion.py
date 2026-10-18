"""
Alternativa evaluada: RANDOM FOREST (aprendizaje automático supervisado) frente a la RED BAYESIANA del proyecto.

Mismo escenario que la tesis (Módulo 3B): los 500 estudiantes de la cohorte con su rendimiento real en notas y un
CHASIDE simulado con el generador «realista», del que se conoce la verdad (interés I*, rendimiento R*).
Partición 70 % entrenamiento / 30 % prueba (semilla 7, igual que el notebook).

Las dos alternativas reciben EXACTAMENTE la misma evidencia por estudiante y área:
  z_int (CHASIDE interés) · z_apt (CHASIDE aptitud) · z_notas · W_efectiva · criterios de calidad.
  · Red bayesiana: NO usa la verdad; aprende sus parámetros de los datos sin etiquetas (como en producción).
  · Random Forest: necesita la verdad para entrenar → se le entrega (ventaja que en la realidad NO existe).

Uso:  python alternativa/comparacion.py      (escribe alternativa/resultados/)
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from modelo import bayes, carreras as mcar, chaside, configuracion as cfg  # noqa: E402
from modelo.constantes import CODIGOS  # noqa: E402

DATOS = os.path.join(RAIZ, "tesis", "notebook", "VocacionalBayesiano_DATOS", "04_procesado")
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
ZONAS = ["vocacion_consolidada", "interes_a_fortalecer", "talento_no_explorado", "no_prioritaria"]


def zona_de(i, r):
    return ZONAS[0] if i > 0 and r > 0 else ZONAS[1] if i > 0 else ZONAS[2] if r > 0 else ZONAS[3]


# ───────────────────────── 1 · Escenario de la tesis (Módulo 3B, generador «realista») ─────────────────────────
ESCENARIOS = {
    "realista": dict(rho_IR=0.2, lam_auto=0.4, sesgo_sd=0.3, kappa=1.7, p_aleatorio=0.03),
    "estres": dict(rho_IR=0.0, lam_auto=0.2, sesgo_sd=0.5, kappa=1.0, p_aleatorio=0.10),
}
COMUN = dict(b_media=-0.4, b_sd=0.4, p_antiguedad={'menos_1_anio': .85, '1_a_2_anios': .10, 'mas_2_anios': .05},
             p_modalidad={'supervisada': .70, 'autonoma': .30}, p_completitud={'completa': .90, 'parcial': .07, 'incompleta': .03},
             blancos={'completa': 0.0, 'parcial': 0.10, 'incompleta': 0.25})


def cargar_notas():
    rend = pd.read_csv(os.path.join(DATOS, "rendimiento_por_area.csv"))
    por_anio = pd.read_csv(os.path.join(DATOS, "rendimiento_por_area_anio.csv"))
    return rend, por_anio


def confiabilidad_notas(por_anio, ids=None):
    d = por_anio if ids is None else por_anio[por_anio['id'].isin(ids)]
    out = {}
    for a in CODIGOS:
        w = d[d['area'] == a].pivot_table(index='id', columns='grado', values='R')
        c = w.corr().values[np.triu_indices(w.shape[1], 1)]
        r = np.nanmean(c); k = w.shape[1]
        out[a] = float(np.clip(k * r / (1 + (k - 1) * r), 0.30, 0.95))
    return out


def simular(rend, por_anio, claves, escenario="realista", semilla=2026):
    """Copia fiel del generador del notebook (celda 3B.2)."""
    P = ESCENARIOS[escenario]
    Zn = rend.pivot(index='id', columns='area', values='R').reindex(columns=CODIGOS)
    Zn = ((Zn - Zn.mean()) / Zn.std()).fillna(0)
    al_obs = confiabilidad_notas(por_anio)
    b_item = np.random.default_rng(99).normal(COMUN['b_media'], COMUN['b_sd'], size=len(claves))
    rng = np.random.default_rng(semilla)
    n = len(Zn)
    al = np.array([al_obs[a] for a in CODIGOS])
    R_v = np.sqrt(al) * Zn.values + np.sqrt(1 - al) * rng.standard_normal((n, 7))
    sesgo = rng.normal(0, P['sesgo_sd'], size=(n, 1)) if P['sesgo_sd'] > 0 else np.zeros((n, 1))
    A_v = P['lam_auto'] * R_v + np.sqrt(1 - P['lam_auto'] ** 2) * rng.standard_normal((n, 7)) + sesgo
    I_v = P['rho_IR'] * R_v + np.sqrt(1 - P['rho_IR'] ** 2) * rng.standard_normal((n, 7))

    def elegir(p): return rng.choice(list(p), size=n, p=list(p.values()))
    antig, modal, compl = elegir(COMUN['p_antiguedad']), elegir(COMUN['p_modalidad']), elegir(COMUN['p_completitud'])
    aleatorio = rng.random(n) < P['p_aleatorio']
    rango = {'menos_1_anio': (1, 11), '1_a_2_anios': (12, 23), 'mas_2_anios': (24, 36)}
    fechas = [(pd.Timestamp('2026-10-01') - pd.DateOffset(months=int(rng.integers(*rango[x])))).strftime('%Y-%m-%d') for x in antig]
    resp = np.empty((n, len(claves)), dtype=object)
    idx = {a: i for i, a in enumerate(CODIGOS)}
    for j, (item, a, t) in enumerate(claves):
        theta = (I_v if t == 'interes' else A_v)[:, idx[a]]
        p = 1 / (1 + np.exp(-(b_item[j] + P['kappa'] * theta)))
        p = np.where(aleatorio, 0.5, p)
        resp[:, j] = np.where(rng.random(n) < p, 1, 0)
    for k, c in enumerate(compl):
        resp[k, rng.random(len(claves)) < COMUN['blancos'][c]] = None
    apps = {i: {"respuestas": {claves[j][0]: resp[k, j] for j in range(len(claves))}, "fecha": fechas[k], "modalidad": modal[k]}
            for k, i in enumerate(Zn.index)}
    verdad = {(i, a): (I_v[k, idx[a]], R_v[k, idx[a]]) for k, i in enumerate(Zn.index) for a in CODIGOS}
    return apps, verdad, {i: bool(aleatorio[k]) for k, i in enumerate(Zn.index)}


# ───────────────────────── 2 · Evidencia común a ambos modelos ─────────────────────────
def evidencia(rend, apps, claves):
    cal = chaside.calibrar(list(apps.values()), claves)
    zn = rend.copy()
    zn['z_notas'] = zn.groupby('area')['R'].transform(lambda s: (s - s.mean()) / s.std())
    ZN = {(r.id, r.area): (r.z_notas, r.W_efectiva) for r in zn.itertuples()}
    EV, CRIT = {}, {}
    for i, ap in apps.items():
        z, crit, _ = chaside.evidencia(ap["respuestas"], ap, cal, claves, pd.Timestamp('2026-10-01').date())
        EV[i] = {a: {"z_int": z[a]["interes"], "z_apt": z[a]["aptitud"],
                     "z_notas": None if pd.isna(ZN[(i, a)][0]) else ZN[(i, a)][0],
                     "W_efectiva": None if pd.isna(ZN[(i, a)][1]) else ZN[(i, a)][1]} for a in CODIGOS}
        CRIT[i] = crit
    return EV, CRIT, cal


# ───────────────────────── 3 · Red bayesiana (sin etiquetas) ─────────────────────────
def bayes_ajustar(EV, por_anio, train, cal):
    alfa_n = confiabilidad_notas(por_anio, train)
    return bayes.aprender(EV, set(train), cal["alfa_chaside"], alfa_n)


def bayes_predecir(EV, CRIT, P, cal, ids, fuentes):
    filas = []
    for i in ids:
        for a in CODIGOS:
            mu, S, _ = bayes.posterior_area(EV[i][a], P[a], cal["alfa_chaside"][a]["interes"], CRIT[i], fuentes)
            z = bayes.zona(mu, S)
            filas.append({"id": i, "area": a, "mu_I": mu[0], "mu_R": mu[1], "sd_I": math.sqrt(S[0][0]), "sd_R": math.sqrt(S[1][1]),
                          "zona": z["clave"], **{f"P_{k}": z["probabilidades"][k] for k in ZONAS}})
    return pd.DataFrame(filas)


# ───────────────────────── 4 · Random Forest (supervisado, con la verdad) ─────────────────────────
def matriz(EV, CRIT, ids):
    filas = []
    for i in ids:
        c = CRIT[i]
        for a in CODIGOS:
            e = EV[i][a]
            filas.append({"id": i, "area": a, "z_int": e["z_int"], "z_apt": e["z_apt"], "z_notas": e["z_notas"],
                          "W": e["W_efectiva"], "completitud": c["completitud_pct"], "autonoma": int(c["modalidad"] == "autonoma"),
                          "antiguedad": {"menos_1_anio": 0, "1_a_2_anios": 1, "mas_2_anios": 2}[c["antiguedad"]],
                          "alerta": int(c["consistencia"] == "alerta"), **{f"area_{x}": int(a == x) for x in CODIGOS}})
    X = pd.DataFrame(filas)
    X[["z_int", "z_apt", "z_notas", "W"]] = X[["z_int", "z_apt", "z_notas", "W"]].astype(float).fillna(0.0)
    return X


COLS = ["z_int", "z_apt", "z_notas", "W", "completitud", "autonoma", "antiguedad", "alerta"] + [f"area_{x}" for x in CODIGOS]


def rf_ajustar(EV, CRIT, verdad, train, semilla=0):
    X = matriz(EV, CRIT, train)
    yI = np.array([verdad[(r.id, r.area)][0] for r in X.itertuples()])
    yR = np.array([verdad[(r.id, r.area)][1] for r in X.itertuples()])
    yZ = np.array([zona_de(i, r) for i, r in zip(yI, yR)])
    kw = dict(n_estimators=300, min_samples_leaf=5, random_state=semilla, n_jobs=-1)
    return (RandomForestRegressor(**kw).fit(X[COLS], yI), RandomForestRegressor(**kw).fit(X[COLS], yR),
            RandomForestClassifier(**kw).fit(X[COLS], yZ))


def rf_predecir(modelos, EV, CRIT, ids, umbral=0.60):
    mI, mR, mZ = modelos
    X = matriz(EV, CRIT, ids)
    out = X[["id", "area"]].copy()
    out["mu_I"], out["mu_R"] = mI.predict(X[COLS]), mR.predict(X[COLS])
    # «incertidumbre» del bosque: dispersión entre árboles (lo usual en la práctica)
    tI = np.stack([t.predict(X[COLS].values) for t in mI.estimators_]); tR = np.stack([t.predict(X[COLS].values) for t in mR.estimators_])
    out["lo_I"], out["hi_I"] = np.percentile(tI, 5, 0), np.percentile(tI, 95, 0)
    out["lo_R"], out["hi_R"] = np.percentile(tR, 5, 0), np.percentile(tR, 95, 0)
    pr = mZ.predict_proba(X[COLS]); clases = list(mZ.classes_)
    for k in ZONAS:
        out[f"P_{k}"] = pr[:, clases.index(k)] if k in clases else 0.0
    mx = out[[f"P_{k}" for k in ZONAS]].max(axis=1)
    out["zona"] = np.where(mx >= umbral, out[[f"P_{k}" for k in ZONAS]].idxmax(axis=1).str[2:], "indeterminado")
    return out


# ───────────────────────── 5 · Métricas (las mismas de la tesis, 5.6) ─────────────────────────
def metricas(df, verdad):
    d = df.copy()
    d["I_v"] = [verdad[(i, a)][0] for i, a in zip(d.id, d.area)]
    d["R_v"] = [verdad[(i, a)][1] for i, a in zip(d.id, d.area)]
    m = {}
    for dim in ("I", "R"):
        m[f"r_{dim}"] = d[f"mu_{dim}"].corr(d[f"{dim}_v"])
        m[f"RMSE_{dim}"] = float(np.sqrt(((d[f"mu_{dim}"] - d[f"{dim}_v"]) ** 2).mean()))
        if f"sd_{dim}" in d:
            m[f"cobertura90_{dim}"] = float((np.abs(d[f"{dim}_v"] - d[f"mu_{dim}"]) <= 1.645 * d[f"sd_{dim}"]).mean())
        else:
            m[f"cobertura90_{dim}"] = float(((d[f"{dim}_v"] >= d[f"lo_{dim}"]) & (d[f"{dim}_v"] <= d[f"hi_{dim}"])).mean())
    d["zona_v"] = [zona_de(i, r) for i, r in zip(d.I_v, d.R_v)]
    det = d[d.zona != "indeterminado"]
    m["exactitud_zona"] = float((det.zona == det.zona_v).mean()) if len(det) else float("nan")
    m["indeterminados"] = 1 - len(det) / len(d)
    m["exactitud_zona_todas"] = float((d[[f"P_{k}" for k in ZONAS]].idxmax(axis=1).str[2:] == d.zona_v).mean())
    P = d[[f"P_{k}" for k in ZONAS]].values
    Y = np.array([[z == zv for z in ZONAS] for zv in d.zona_v], dtype=float)
    m["brier"] = float(((P - Y) ** 2).sum(axis=1).mean())
    top_v = d.loc[d.groupby("id")["I_v"].idxmax()].set_index("id")["area"]
    top3 = d.sort_values("mu_I", ascending=False).groupby("id")["area"].apply(lambda s: set(s[:3]))
    m["top1_en_top3"] = float(np.mean([top_v[i] in top3[i] for i in top3.index]))
    return m


def ranking_carreras(df, verdad, lista_car, calib_car, k=5):
    perfil = mcar.matriz_perfil(lista_car); WN = mcar.pesos_carrera(perfil, calib_car["gamma"])
    comun, uno = [], []
    for i, g in df.groupby("id"):
        g = g.set_index("area").reindex(CODIGOS)
        MU = g[["mu_I", "mu_R"]].values
        MUv = np.array([verdad[(i, a)] for a in CODIGOS])
        A, Av = mcar.afinidad(MU, WN, calib_car["normas"]), mcar.afinidad(MUv, WN, calib_car["normas"])
        t, tv = set(np.argsort(-A)[:k]), set(np.argsort(-Av)[:k])
        comun.append(len(t & tv)); uno.append(int(np.argmax(Av) in t))
    return {"top5_en_comun": float(np.mean(comun)), "carrera1_real_en_top5": float(np.mean(uno))}


def main():
    os.makedirs(SALIDA, exist_ok=True)
    claves = cfg.cargar_claves(); lista_car, _ = cfg.cargar_carreras(); fuentes = cfg.cargar_fuentes()
    with open(os.path.join(RAIZ, "config", "calibracion_referencia.json"), encoding="utf-8") as f:
        calib_car = json.load(f)["carreras"]
    rend, por_anio = cargar_notas()
    res = {}
    for esc in ("realista", "estres"):
        apps, verdad, aleat = simular(rend, por_anio, claves, esc)
        EV, CRIT, cal = evidencia(rend, apps, claves)
        train, test = bayes.particion(EV.keys())
        train, test = sorted(train), sorted(test)
        P = bayes_ajustar(EV, por_anio, train, cal)
        pb = bayes_predecir(EV, CRIT, P, cal, test, fuentes)
        prf = rf_predecir(rf_ajustar(EV, CRIT, verdad, train), EV, CRIT, test)
        res[esc] = {"Red bayesiana": {**metricas(pb, verdad), **ranking_carreras(pb, verdad, lista_car, calib_car)},
                    "Random Forest": {**metricas(prf, verdad), **ranking_carreras(prf, verdad, lista_car, calib_car)}}
        if esc == "realista":
            pb.to_csv(os.path.join(SALIDA, "predicciones_bayes.csv"), index=False)
            prf.to_csv(os.path.join(SALIDA, "predicciones_rf.csv"), index=False)
            # Curva de aprendizaje: ¿qué pasa con pocos estudiantes?
            curva = []
            rng = np.random.default_rng(1)
            for n in (20, 50, 100, 200, 350):
                for rep in range(5 if n < 350 else 1):
                    sub = sorted(rng.choice(train, size=n, replace=False)) if n < len(train) else train
                    Pn = bayes_ajustar(EV, por_anio, sub, cal)
                    mb = metricas(bayes_predecir(EV, CRIT, Pn, cal, test, fuentes), verdad)
                    mr = metricas(rf_predecir(rf_ajustar(EV, CRIT, verdad, sub, semilla=rep), EV, CRIT, test), verdad)
                    curva += [{"n_entrenamiento": n, "modelo": "Red bayesiana", **mb}, {"n_entrenamiento": n, "modelo": "Random Forest", **mr}]
            curva = pd.DataFrame(curva).groupby(["n_entrenamiento", "modelo"]).mean(numeric_only=True).reset_index()
            curva.to_csv(os.path.join(SALIDA, "curva_aprendizaje.csv"), index=False)
            res["curva"] = curva.to_dict("records")
            # Importancia de variables del RF (lo único «explicable» que ofrece)
            mI, mR, _ = rf_ajustar(EV, CRIT, verdad, train)
            res["importancia_rf"] = {"interes": dict(zip(COLS, np.round(mI.feature_importances_, 3))),
                                     "rendimiento": dict(zip(COLS, np.round(mR.feature_importances_, 3)))}
            res["n"] = {"entrenamiento": len(train), "prueba": len(test)}
    with open(os.path.join(SALIDA, "resumen.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    tabla = pd.DataFrame({f"{esc} · {mod}": v for esc in ("realista", "estres") for mod, v in res[esc].items()}).T
    tabla.to_csv(os.path.join(SALIDA, "comparacion.csv"))
    print(tabla.round(3).T.to_string())
    print(pd.DataFrame(res["curva"])[["n_entrenamiento", "modelo", "r_I", "r_R", "cobertura90_I", "exactitud_zona", "brier"]].round(3).to_string(index=False))
    return res


if __name__ == "__main__":
    main()
