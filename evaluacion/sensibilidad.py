"""Sensibilidad: aprendizaje robusto (A2) y objetivo del umbral (0,90 / 0,92) en escenarios realista y estrés.
Uso: python evaluacion/sensibilidad.py   (~1 min; escribe evaluacion/resultados/sensibilidad_umbral_robusto.csv)"""
import os
import sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validacion_cruzada as vc
from validacion_cruzada import cmp, cfg, KFold
claves = cfg.cargar_claves(); fuentes = cfg.cargar_fuentes(); rend, por_anio = cmp.cargar_notas()
filas = []
for esc in ("realista", "estres"):
    for semilla in vc.SEMILLAS:
        apps, verdad, _ = cmp.simular(rend, por_anio, claves, esc, semilla=semilla)
        ids = np.array(sorted(apps))
        for f, (a, b) in enumerate(KFold(5, shuffle=True, random_state=7).split(ids)):
            train, test = sorted(ids[a]), sorted(ids[b])
            EV1, CRIT1, cal1 = vc.evidencia(rend, apps, claves, train)
            for rob in (False, True):
                P = vc.aprender(EV1, CRIT1, por_anio, train, cal1, robusto=rob)
                ptr = cmp.bayes_predecir(EV1, CRIT1, P, cal1, train, fuentes)
                pte = cmp.bayes_predecir(EV1, CRIT1, P, cal1, test, fuentes)
                for obj in (0.90, 0.92):
                    vc.OBJETIVO_EXACTITUD = obj
                    u, esp, _ = vc.elegir_umbral(ptr)
                    m = cmp.metricas(vc.aplicar_umbral(pte, u), verdad)
                    filas.append({"esc": esc, "semilla": semilla, "fold": f, "robusto": rob, "objetivo": obj, "umbral": u, "esperada": esp, **m})
                m = cmp.metricas(vc.aplicar_umbral(pte, 0.60), verdad)
                filas.append({"esc": esc, "semilla": semilla, "fold": f, "robusto": rob, "objetivo": 0.0, "umbral": 0.6, "esperada": np.nan, **m})
df = pd.DataFrame(filas)
df.to_csv(os.path.join(vc.SALIDA, 'sensibilidad_umbral_robusto.csv'), index=False)
g = df.groupby(["esc", "robusto", "objetivo"])[["umbral", "esperada", "exactitud_zona", "indeterminados", "exactitud_zona_todas", "brier", "cobertura90_I", "cobertura90_R", "r_I"]]
print(g.mean().round(4).to_string()); print(g.std().round(4).to_string())
# pareado robusto vs no robusto en estres (objetivo 0)
for esc in ("realista","estres"):
    A = df[(df.esc==esc)&(df.robusto)&(df.objetivo==0)].set_index(["semilla","fold"]); B = df[(df.esc==esc)&(~df.robusto)&(df.objetivo==0)].set_index(["semilla","fold"])
    for m in ["brier","cobertura90_I","r_I","exactitud_zona_todas"]:
        print(esc, m, vc.ic95((A[m]-B[m]).values))
