"""
Módulo 9 · Contrato de datos con la interfaz: estudiantes/<id>.json, cohorte.json y carreras.json.
Mismo formato que el notebook de la tesis, para que la interfaz funcione sin cambios.
"""
from __future__ import annotations

import math
from datetime import date, datetime

import numpy as np

from . import bayes, carreras as mcar, notas
from .calibracion import evidencia_estudiante, posterior_matrices
from .constantes import CODIGOS, EJES, RUBRICA, VERSION_CONTRATO


def limpio(x):
    """Tipos numpy → JSON estándar; floats a 3 decimales; NaN → null (notebook 9.1)."""
    if isinstance(x, dict):
        return {k: limpio(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [limpio(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if math.isnan(x) else round(float(x), 3)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def evaluar_estudiante(estudiante: dict, prep: dict, aplicacion: dict, calib: dict, claves, lista_carreras: list[dict],
                       fecha_ref: date | None = None, fuentes: dict | None = None, generado: str | None = None) -> dict:
    """Núcleo completo (notas + CHASIDE) → JSON del estudiante. estudiante: {id, nombre, genero, nombre_ficticio}."""
    fecha_ref = fecha_ref or date.today()
    x = evidencia_estudiante(prep, aplicacion, calib, claves, fecha_ref)
    ev, crit, rend, aporte, por_anio = x["ev"], x["crit"], x["rend"], x["aporte"], x["por_anio"]
    MU, SIG, aportes = posterior_matrices(ev, crit, calib, fuentes)
    T = max((g for (_, g) in por_anio), default=None)
    areas = []
    for k, a in enumerate(CODIGOS):
        mu, S, ap = MU[k], SIG[k], aportes[k]
        p = calib["param"][a]
        areas.append({
            "codigo": a, "nombre": EJES[a],
            "interes": bayes.eje(float(mu[0]), math.sqrt(S[0][0])), "rendimiento": bayes.eje(float(mu[1]), math.sqrt(S[1][1])),
            "zona": bayes.zona(mu, S, calib["umbral_certeza"]),
            "autopercepcion": bayes.autopercepcion(ev[a]["z_apt"], ev[a]["z_notas"], p["r_apt_notas"]),
            "aportes": {"interes": {"chaside_interes": float(ap["chaside_interes"][0]) if "chaside_interes" in ap else None},
                        "rendimiento": {"notas": float(ap["notas"][1]) if "notas" in ap else None,
                                        "autopercepcion": float(ap["autopercepcion"][1]) if "autopercepcion" in ap else None}},
            "materias_clave": notas.materias_clave(aporte, a, T) if T is not None else [],
            "evidencia": ev[a]})
    carreras = mcar.ranking(areas, MU, SIG, lista_carreras, calib["carreras"], calib["beta"], calib["n_sim"], calib["top_k"])
    grados = sorted({g for (_, g) in por_anio})
    alertas = []
    if crit.get("consistencia") == "alerta":
        alertas.append({"tipo": "consistencia", "texto": "CHASIDE con respuestas poco diferenciadas: confirmar intereses en entrevista."})
    if crit.get("completitud") and crit["completitud"] != "completa":
        alertas.append({"tipo": "completitud", "texto": f"CHASIDE {crit['completitud']} ({crit['completitud_pct']} % respondido)."})
    if crit.get("antiguedad") and crit["antiguedad"] != "menos_1_anio":
        alertas.append({"tipo": "antiguedad", "texto": "CHASIDE aplicado hace más de un año: los intereses pueden haber cambiado."})
    if crit.get("modalidad") == "autonoma":
        alertas.append({"tipo": "modalidad", "texto": "CHASIDE respondido sin supervisión: su confiabilidad se ajustó a la baja."})
    if len(grados) < 2:
        alertas.append({"tipo": "notas", "texto": f"Solo hay notas de {len(grados)} año: el rendimiento tiene menos respaldo."})
    n_ind = sum(a["zona"]["clave"] == "indeterminado" for a in areas)
    if n_ind >= 3:
        alertas.append({"tipo": "indeterminado", "texto": f"{n_ind} de 7 áreas sin zona clara: falta evidencia (sumar entrevista u otra prueba)."})
    ga = prep.get("grado_actual") or (max(grados) if grados else None)
    return limpio({
        "version": VERSION_CONTRATO, "generado": generado or datetime.now().isoformat(timespec="seconds"),
        "estudiante": {**{k: estudiante.get(k) for k in ("id", "nombre", "genero", "nombre_ficticio")}, "grado_actual": ga,
                       "fuentes": {"notas": {"anios": grados, "materias": len({x["materia"] for x in aporte})},
                                   "chaside": {"fecha": aplicacion.get("fecha"), "modalidad": crit.get("modalidad"),
                                               "completitud": crit.get("completitud"), "consistencia": crit.get("consistencia")},
                                   "ippj": None}},
        "areas": areas,
        "trayectoria": notas.trayectoria(por_anio, calib["notas"]["normas_trayectoria"]),
        "carreras": carreras, "alertas": alertas,
        "origen": {"notas": notas.origen_notas(prep["filas"]), "chaside": x["origen_chaside"]},
        "parametros": {"umbral_certeza": calib["umbral_certeza"], "peso_interes_carreras": calib["beta"],
                       "simulaciones_monte_carlo": calib["n_sim"]}})


def entrada_indice(r: dict) -> dict:
    e = r["estudiante"]
    return {"id": e["id"], "nombre": e["nombre"], "genero": e["genero"], "nombre_ficticio": e["nombre_ficticio"],
            "grado_actual": e["grado_actual"], "top3": [c["nombre"] for c in r["carreras"][:3]],
            "vocacion_consolidada": [a["codigo"] for a in r["areas"] if a["zona"]["clave"] == "vocacion_consolidada"],
            "perfil": {a["codigo"]: [a["interes"]["percentil"], a["rendimiento"]["percentil"], a["zona"]["clave"]] for a in r["areas"]},
            "n_alertas": len(r["alertas"])}


def modelo_web(calib: dict, claves, preguntas: dict | None = None, origen_preguntas: str | None = None) -> dict:
    """Lo que la interfaz necesita para recalcular en el navegador si se repite el CHASIDE."""
    m = {"claves": [[i, a, t] for i, a, t in claves], "normas_chaside": calib["chaside"]["normas_chaside"],
         "consistencia": calib["chaside"]["consistencia"], "alfa_chaside": calib["chaside"]["alfa_chaside"],
         "param": calib["param"], "rubrica": RUBRICA, "umbral_certeza": calib["umbral_certeza"], "n_sim": calib["n_sim"],
         "top_k": calib["top_k"], "beta": calib["beta"]}
    if preguntas:
        m["preguntas"] = {str(k): v for k, v in sorted(preguntas.items())}
        m["preguntas_origen"] = origen_preguntas
    return m


def cohorte_json(indice: list[dict], calib: dict, claves, preguntas=None, origen_preguntas=None) -> dict:
    zonas = {}
    for e in indice:
        for _, _, z in e["perfil"].values():
            zonas[z] = zonas.get(z, 0) + 1
    tot = sum(zonas.values()) or 1
    return limpio({"version": VERSION_CONTRATO, "generado": calib.get("fecha"), "n_estudiantes": len(indice),
                   "parametros": {"umbral_certeza": calib["umbral_certeza"], "peso_interes_carreras": calib["beta"]},
                   "resumen_zonas": {k: v / tot for k, v in sorted(zonas.items(), key=lambda t: -t[1])},
                   "evaluacion": calib.get("evaluacion"), "modelo": modelo_web(calib, claves, preguntas, origen_preguntas),
                   "estudiantes": indice})


def carreras_json(calib: dict, lista_carreras: list[dict], pais: str = "EC", fuente: str = "carreras_EC.csv") -> dict:
    return limpio({"version": VERSION_CONTRATO, "generado": calib.get("fecha"), "pais": pais, "fuente": fuente,
                   "gamma": calib["carreras"]["gamma"], "normas": calib["carreras"]["normas"],
                   "areas": [{"codigo": a, "nombre": EJES[a]} for a in CODIGOS],
                   "carreras": lista_carreras})
