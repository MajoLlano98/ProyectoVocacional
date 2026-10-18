"""
Construye config/calibracion_referencia.json a partir de las salidas oficiales del notebook de la tesis
y valida, etapa por etapa, que el paquete modelo/ reproduce el notebook.

Uso:  python scripts/calibracion_referencia.py RUTA_A/Vocacional_MIA
      (carpeta con INTERFAZ/datos y SISTEMA/VocacionalBayesiano_DATOS)
"""
import csv
import glob
import json
import math
import os
import sys
from datetime import date

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from modelo import bayes, carreras as mcar, configuracion as cfg, notas  # noqa: E402
from modelo.calibracion import posterior_matrices  # noqa: E402
from modelo.constantes import CODIGOS  # noqa: E402
from modelo.resultado import evaluar_estudiante  # noqa: E402


def leer_csv(ruta):
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(x):
    return None if x in ("", None) else float(x)


def registros_desde_origen(est):
    """Reconstruye las filas del reporte a partir del detalle de notas exportado (escala 0–10, 3 decimales)."""
    regs = []
    for y in est["origen"]["notas"]:
        for m in y["materias"]:
            base = {"id_colegio": est["estudiante"]["id"], "grado_actual": est["estudiante"]["grado_actual"],
                    "grado": y["grado"], "materia": m["materia"], "letra": ""}
            if m["sem1"] is not None:
                regs.append({**base, "anio": f"{y['periodo']} Sem 1", "nota": m["sem1"]})
            if m["sem2"] is not None:
                regs.append({**base, "anio": f"{y['periodo']} Sem 2", "nota": m["sem2"]})
            if m["sem1"] is None and m["sem2"] is None and m["final"] is not None:
                regs.append({**base, "anio": y["periodo"], "nota": m["final"]})
    return regs


def main(base):
    S = os.path.join(base, "SISTEMA", "VocacionalBayesiano_DATOS")
    WEB = os.path.join(base, "INTERFAZ", "datos")
    coh = json.load(open(os.path.join(WEB, "cohorte.json"), encoding="utf-8"))
    kar = json.load(open(os.path.join(WEB, "carreras.json"), encoding="utf-8"))
    EST = {os.path.basename(p)[:-5]: json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(WEB, "estudiantes", "*.json"))}
    reglas = cfg.cargar_mapeo()
    claves = cfg.cargar_claves()
    lista_car, malas = cfg.cargar_carreras()
    fuentes = cfg.cargar_fuentes()
    M = coh["modelo"]
    rep = {}

    # ── Módulo 3: notas ─────────────────────────────────────────────
    PREP = {i: notas.preparar(registros_desde_origen(e), reglas) for i, e in EST.items()}
    nm = notas.ajustar_normas_materias([p["por_materia"] for p in PREP.values()])
    REND, PA, APORTE = {}, {}, {}
    for i, p in PREP.items():
        APORTE[i], PA[i], REND[i] = notas.rendimiento(p["por_materia"], nm)
    of = {(r["id"], r["area"]): r for r in leer_csv(os.path.join(S, "04_procesado", "rendimiento_por_area.csv"))}
    eR = max(abs(REND[i][a]["R"] - f(r["R"])) for (i, a), r in of.items() if r["R"])
    eW = max(abs(REND[i][a]["W_efectiva"] - f(r["W_efectiva"])) for (i, a), r in of.items() if r["R"])
    rep["Módulo 3 · R por área (máx |dif|)"] = eR
    rep["Módulo 3 · W_efectiva (máx |dif|)"] = eW
    na = notas.ajustar_normas_area(list(REND.values()))
    nt = notas.ajustar_normas_trayectoria(list(PA.values()))
    ZN = {i: notas.z_notas(REND[i], na) for i in EST}
    rep["Módulo 5.1 · z_notas vs JSON (máx |dif|)"] = max(abs(ZN[i][a["codigo"]] - a["evidencia"]["z_notas"])
                                                         for i, e in EST.items() for a in e["areas"])
    rep["Módulo 9 · trayectoria percentil (máx |dif|)"] = max(
        abs(t1["rendimiento_percentil"] - t2["rendimiento_percentil"])
        for i, e in EST.items() for t1, t2 in zip(notas.trayectoria(PA[i], nt), e["trayectoria"]))

    # ── Módulo 4: evidencia CHASIDE oficial (las respuestas ítem a ítem no salen del Drive) ──
    chev = {}
    for r in leer_csv(os.path.join(S, "04_procesado", "chaside_evidencia.csv")):
        chev.setdefault(r["id"], {})[r["area"]] = r
    alfa_ch = {a: {t: M["alfa_chaside"][a][t] for t in ("interes", "aptitud")} for a in CODIGOS}

    # ── Módulo 5: aprendizaje ───────────────────────────────────────
    EV = {i: {a: {"z_int": f(chev[i][a]["z_int"]), "z_apt": f(chev[i][a]["z_apt"]), "z_notas": ZN[i].get(a),
                  "W_efectiva": REND[i][a]["W_efectiva"] if a in REND[i] else None} for a in CODIGOS} for i in EST}
    CRIT = {i: {k: chev[i]["C"][k] for k in ("antiguedad", "modalidad", "completitud", "consistencia")} for i in EST}
    train, test = bayes.particion(EV.keys())
    alfa_n = notas.confiabilidad_notas(PA, train)
    P = bayes.aprender(EV, train, alfa_ch, alfa_n)
    rep["Módulo 5.2 · parámetros aprendidos (máx |dif|)"] = max(abs(P[a][k] - M["param"][a][k]) for a in CODIGOS for k in P[a])
    calib = {"version": "1.0", "origen": "referencia_tesis", "fecha": coh["generado"], "umbral_certeza": M["umbral_certeza"],
             "beta": M["beta"], "n_sim": M["n_sim"], "top_k": M["top_k"],
             "notas": {"normas_materias": nm, "normas_area": na, "normas_trayectoria": nt,
                       "alfa_notas_observada": notas.confiabilidad_notas(PA)},
             "chaside": {"normas_chaside": M["normas_chaside"], "alfa_chaside": alfa_ch, "consistencia": M["consistencia"]},
             "param": P, "evaluacion": coh.get("evaluacion")}
    post = {(r["id"], r["area"]): r for r in leer_csv(os.path.join(S, "05_salidas", "posterior_por_area.csv"))}
    MUS = {}
    err_mu = err_sd = 0.0; zonas_dif = 0
    for i in EST:
        MU, SIG, _ = posterior_matrices(EV[i], CRIT[i], calib, fuentes)
        MUS[i] = (MU, SIG)
        for k, a in enumerate(CODIGOS):
            o = post[(i, a)]
            err_mu = max(err_mu, abs(MU[k][0] - f(o["mu_I"])), abs(MU[k][1] - f(o["mu_R"])))
            err_sd = max(err_sd, abs(math.sqrt(SIG[k][0][0]) - f(o["sd_I"])), abs(math.sqrt(SIG[k][1][1]) - f(o["sd_R"])))
            z = bayes.zona(MU[k], SIG[k])["clave"]
            zonas_dif += z != [x for x in EST[i]["areas"] if x["codigo"] == a][0]["zona"]["clave"]
    rep["Módulo 5.3 · μ posterior (máx |dif|)"] = err_mu
    rep["Módulo 5.3 · σ posterior (máx |dif|)"] = err_sd
    rep["Módulo 5.3 · zonas distintas (de 3500)"] = zonas_dif

    # ── Módulo 7: carreras ──────────────────────────────────────────
    perfil = mcar.matriz_perfil(lista_car)
    gamma, tabla = mcar.elegir_gamma([m for m, _ in MUS.values()], perfil)
    normas_c = mcar.ajustar_normas([m for m, _ in MUS.values()], mcar.pesos_carrera(perfil, gamma))
    rep["Módulo 7 · γ elegido"] = f"{gamma} (tesis: {kar['gamma']})"
    rep["Módulo 7 · normas de afinidad (máx |dif|)"] = max(abs(x - y) for b in normas_c for k in ("media", "sd")
                                                           for x, y in zip(normas_c[b][k], kar["normas"][b][k]))
    rep["Módulo 7 · ids de carreras iguales a la tesis"] = [c["id"] for c in lista_car] == [c["id"] for c in kar["carreras"]]
    calib["carreras"] = {"gamma": gamma, "tabla_gamma": tabla, "normas": normas_c, "ids": [c["id"] for c in lista_car]}
    # posiciones (μ) de la cohorte, sin IDs: permiten recalcular normas si el colegio cambia el catálogo de carreras
    calib["mus_cohorte"] = [np.round(m, 4).tolist() for m, _ in MUS.values()]
    rk = {}
    for r in leer_csv(os.path.join(S, "05_salidas", "ranking_carreras.csv")):
        rk.setdefault(r["id"], {})[r["carrera_id"]] = r
    WN = mcar.pesos_carrera(perfil, gamma)
    err_af = 0.0
    for i, (MU, _) in MUS.items():
        A = mcar.afinidad(MU, WN, normas_c)
        for cid, r in rk[i].items():
            err_af = max(err_af, abs(A[[c["id"] for c in lista_car].index(cid)] - f(r["afinidad"])))
    rep["Módulo 7 · afinidad (máx |dif|, la tesis redondea a 0.1)"] = err_af

    # ── Módulo 9: JSON completo de un estudiante (sin respuestas ítem a ítem: z del CHASIDE oficial) ──
    calib["detalle"] = {"construida_con": "scripts/calibracion_referencia.py", "n_cohorte": len(EST)}
    with open(os.path.join(RAIZ, "config", "calibracion_referencia.json"), "w", encoding="utf-8") as fh:
        json.dump(calib, fh, ensure_ascii=False, separators=(",", ":"))
    print("\nVALIDACIÓN contra la tesis")
    for k, v in rep.items():
        print(f"  {k:58s} {v if isinstance(v, (str, bool, int)) else f'{v:.6f}'}")
    print(f"\n✓ config/calibracion_referencia.json ({os.path.getsize(os.path.join(RAIZ, 'config', 'calibracion_referencia.json')) / 1e3:.0f} KB)")
    return rep, calib, PREP, EST


if __name__ == "__main__":
    main(sys.argv[1])
