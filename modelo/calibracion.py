"""
Calibración de la cohorte: todo lo que el modelo «aprende» de los datos del colegio.

Separar calibración (cohorte completa, se hace de vez en cuando) de inferencia (un estudiante, al instante)
permite que el servidor procese a cada estudiante apenas llegan sus datos, con los parámetros vigentes.

Qué se recalibra y con cuántos estudiantes como mínimo (si no se alcanza, se conserva la calibración previa):
  · normas de notas (materia×grado, grado, área, trayectoria) ........ MIN_NOTAS estudiantes con notas
  · normas CHASIDE, KR-20 y umbral de consistencia ................... MIN_CHASIDE aplicaciones
  · parámetros latentes α notas, λ, ρ, W_med (partición 70/30) ........ MIN_APRENDER con núcleo completo
  · γ y normas de afinidad de carreras .............................. MIN_APRENDER con núcleo completo
  · umbral de certeza de zonas (v1.1, sin etiquetas) ................. MIN_APRENDER con núcleo completo
"""
from __future__ import annotations

import copy
from datetime import date, datetime

import numpy as np

from . import bayes, carreras as mcar, chaside, notas
from .constantes import BETA_INTERES, CODIGOS, N_SIM, TOP_K, UMBRAL_CERTEZA

MIN_NOTAS = 30
MIN_CHASIDE = 30
MIN_APRENDER = 100


def evidencia_estudiante(prep: dict, aplicacion: dict | None, calib: dict, claves, fecha_ref: date):
    """Evidencia completa de un estudiante con la calibración dada."""
    aporte, por_anio, rend = notas.rendimiento(prep["por_materia"], calib["notas"]["normas_materias"])
    zn = notas.z_notas(rend, calib["notas"]["normas_area"])
    if aplicacion:
        zc, crit, origen_ch = chaside.evidencia(aplicacion["respuestas"], aplicacion, calib["chaside"], claves, fecha_ref)
    else:
        zc, crit, origen_ch = {a: {"interes": None, "aptitud": None} for a in CODIGOS}, {}, None
    ev = {a: {"z_int": zc[a]["interes"], "z_apt": zc[a]["aptitud"], "z_notas": zn.get(a),
              "W_efectiva": rend[a]["W_efectiva"] if a in rend else None} for a in CODIGOS}
    return {"ev": ev, "crit": crit, "origen_chaside": origen_ch, "aporte": aporte, "por_anio": por_anio, "rend": rend}


def posterior_matrices(ev: dict, crit: dict, calib: dict, fuentes: dict | None = None):
    MU, SIG, extra = np.zeros((7, 2)), np.zeros((7, 2, 2)), []
    for k, a in enumerate(CODIGOS):
        mu, S, ap = bayes.posterior_area(ev[a], calib["param"][a], calib["chaside"]["alfa_chaside"][a]["interes"], crit, fuentes)
        MU[k], SIG[k] = mu, S
        extra.append(ap)
    return MU, SIG, extra


def calibrar(cohorte: list[dict], claves, lista_carreras: list[dict], previa: dict, fecha_ref: date | None = None,
             fuentes: dict | None = None, minimos: dict | None = None) -> dict:
    """cohorte: [{id, prep (notas.preparar), chaside: {respuestas, fecha, modalidad} | None}]."""
    fecha_ref = fecha_ref or date.today()
    mins = {"notas": MIN_NOTAS, "chaside": MIN_CHASIDE, "aprender": MIN_APRENDER, **(minimos or {})}
    cal = copy.deepcopy(previa)
    hecho = {}
    con_notas = [e for e in cohorte if e["prep"]["por_materia"]]
    con_ch = [e for e in cohorte if e.get("chaside")]

    # 1 · notas
    if len(con_notas) >= mins["notas"]:
        nm = notas.ajustar_normas_materias([e["prep"]["por_materia"] for e in con_notas])
        rends, por_anios = {}, {}
        for e in con_notas:
            _, pa, r = notas.rendimiento(e["prep"]["por_materia"], nm)
            rends[e["id"]], por_anios[e["id"]] = r, pa
        cal["notas"] = {"normas_materias": nm, "normas_area": notas.ajustar_normas_area(list(rends.values())),
                        "normas_trayectoria": notas.ajustar_normas_trayectoria(list(por_anios.values())),
                        "alfa_notas_observada": notas.confiabilidad_notas(por_anios)}
        hecho["notas"] = len(con_notas)
    else:
        por_anios = {}

    # 2 · CHASIDE
    if len(con_ch) >= mins["chaside"]:
        nuevo = chaside.calibrar([e["chaside"] for e in con_ch], claves)
        for a in CODIGOS:                               # α no calculable (pocas respuestas completas) → se conserva el previo
            for t in ("interes", "aptitud"):
                if nuevo["alfa_chaside"][a][t] is None:
                    nuevo["alfa_chaside"][a][t] = previa["chaside"]["alfa_chaside"][a][t]
        cal["chaside"] = nuevo
        hecho["chaside"] = len(con_ch)

    # 3 · aprendizaje (núcleo completo)
    nucleo = [e for e in cohorte if e["prep"]["por_materia"] and e.get("chaside")]
    if len(nucleo) >= mins["aprender"]:
        EV, CRIT = {}, {}
        for e in nucleo:
            x = evidencia_estudiante(e["prep"], e["chaside"], cal, claves, fecha_ref)
            EV[e["id"]], CRIT[e["id"]] = x["ev"], x["crit"]
            por_anios.setdefault(e["id"], x["por_anio"])
        train, test = bayes.particion(EV.keys())
        alfa_n = notas.confiabilidad_notas(por_anios, train)
        cal["param"] = bayes.aprender(EV, train, cal["chaside"]["alfa_chaside"], alfa_n)
        hecho["aprender"] = {"entrenamiento": len(train), "prueba": len(test)}
        # 4 · carreras
        post = [posterior_matrices(EV[i], CRIT[i], cal, fuentes) for i in EV]
        MUs = [m for m, _, _ in post]
        # 5 · umbral de certeza (v1.1): exactitud esperada ≥ objetivo, calculada por el propio modelo
        certezas = [bayes.zona(m[k], S[k])["certeza"] for m, S, _ in post for k in range(len(CODIGOS))]
        eleccion = bayes.elegir_umbral(certezas)
        cal["umbral_certeza"] = eleccion["umbral"]
        hecho["umbral"] = eleccion
        perfil = mcar.matriz_perfil(lista_carreras)
        gamma, tabla = mcar.elegir_gamma(MUs, perfil, BETA_INTERES)
        cal["carreras"] = {"gamma": gamma, "tabla_gamma": tabla,
                           "normas": mcar.ajustar_normas(MUs, mcar.pesos_carrera(perfil, gamma)),
                           "ids": [c["id"] for c in lista_carreras]}
        cal["mus_cohorte"] = [np.round(m, 4).tolist() for m in MUs]
        hecho["carreras"] = len(MUs)

    cal["origen"] = "cohorte" if hecho else previa.get("origen", "referencia")
    cal["version"] = "1.1"
    cal["fecha"] = datetime.now().isoformat(timespec="seconds")
    cal["detalle"] = {"recalibrado": hecho, "n_cohorte": len(cohorte), "n_con_notas": len(con_notas),
                      "n_con_chaside": len(con_ch), "n_nucleo": len(nucleo), "minimos": mins,
                      "conservado_de_previa": [k for k in ("notas", "chaside", "aprender", "carreras", "umbral") if k not in hecho]}
    return cal


def ajustar_catalogo(cal: dict, lista_carreras: list[dict]) -> dict:
    """Si el catálogo de carreras cambió, recalcula γ y normas con las posiciones guardadas de la cohorte."""
    ids = [c["id"] for c in lista_carreras]
    if cal.get("carreras") and cal["carreras"].get("ids") == ids:
        return cal
    if not cal.get("mus_cohorte"):
        raise ValueError("El catálogo de carreras cambió y no hay posiciones de la cohorte para recalcular sus normas.")
    MUs = [np.array(m) for m in cal["mus_cohorte"]]
    perfil = mcar.matriz_perfil(lista_carreras)
    gamma, tabla = mcar.elegir_gamma(MUs, perfil, cal.get("beta", BETA_INTERES))
    cal = copy.deepcopy(cal)
    cal["carreras"] = {"gamma": gamma, "tabla_gamma": tabla, "normas": mcar.ajustar_normas(MUs, mcar.pesos_carrera(perfil, gamma)),
                       "ids": ids}
    return cal


def base_vacia() -> dict:
    return {"version": "1.0", "origen": "vacia", "umbral_certeza": UMBRAL_CERTEZA, "beta": BETA_INTERES,
            "n_sim": N_SIM, "top_k": TOP_K, "notas": None, "chaside": None, "param": None, "carreras": None,
            "evaluacion": None}
