"""
Módulo 4 · Adaptador CHASIDE: 98 respuestas Sí/No → evidencia de interés y autopercepción por área.

Reproduce el notebook 4.2–4.5: proporción de "Sí" por área y escala, normas y KR-20 de la cohorte,
criterios de calidad de cada aplicación (antigüedad, modalidad, completitud, consistencia) y escala z.
"""
from __future__ import annotations

import math
from datetime import date, datetime

import numpy as np

from .constantes import CODIGOS, TIPOS_CHASIDE
from .estadistica import cuantil, media_sd

MAPA_SI = {"sí": 1, "si": 1, "1": 1, "true": 1, "x": 1, "s": 1, "no": 0, "0": 0, "false": 0, "n": 0}


def normalizar_respuesta(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
        return 1 if v == 1 else 0 if v == 0 else None
    return MAPA_SI.get(str(v).strip().lower())


def items_por_escala(claves):
    out = {(a, t): [] for a in CODIGOS for t in TIPOS_CHASIDE}
    for item, a, t in claves:
        out[(a, t)].append(item)
    return out


def puntajes(respuestas: dict, claves) -> dict:
    """{item: 1/0/None} → {(area, tipo): proporción de Sí entre los respondidos, o None}."""
    out = {}
    for (a, t), items in items_por_escala(claves).items():
        r = [respuestas.get(i) for i in items]
        r = [x for x in r if x in (0, 1)]
        out[(a, t)] = sum(r) / len(r) if r else None
    return out


def dispersion_interes(punt: dict):
    v = [punt[(a, "interes")] for a in CODIGOS if punt[(a, "interes")] is not None]
    return media_sd(v)[1] if len(v) >= 2 else None


# ───────────────────────── calibración de la cohorte ─────────────────────────
def kr20(matriz: np.ndarray) -> float:
    """KR-20 con los estudiantes que respondieron todos los ítems de la escala."""
    X = matriz[~np.isnan(matriz).any(axis=1)]
    if len(X) < 3:
        return float("nan")
    k, p = X.shape[1], X.mean(axis=0)
    var_tot = X.sum(axis=1).var(ddof=1)
    if var_tot == 0:
        return float("nan")
    return float(k / (k - 1) * (1 - (p * (1 - p)).sum() / var_tot))


def calibrar(aplicaciones: list[dict], claves) -> dict:
    """aplicaciones: [{respuestas:{item:0/1/None}}] → normas, α (KR-20) y umbral de consistencia."""
    esc = items_por_escala(claves)
    punts = [puntajes(ap["respuestas"], claves) for ap in aplicaciones]
    normas, alfa = {}, {}
    for a in CODIGOS:
        normas[a], alfa[a] = {}, {}
        for t in TIPOS_CHASIDE:
            m, sd, _ = media_sd([p[(a, t)] for p in punts])
            normas[a][t] = [m, sd]
            M = np.array([[np.nan if ap["respuestas"].get(i) not in (0, 1) else ap["respuestas"][i] for i in esc[(a, t)]]
                          for ap in aplicaciones], dtype=float)
            k = kr20(M)
            alfa[a][t] = float(np.clip(k, 0.30, 0.95)) if not math.isnan(k) else None
    disp = [dispersion_interes(p) for p in punts]
    return {"normas_chaside": normas, "alfa_chaside": alfa,
            "consistencia": {"disp_p05": cuantil(disp, 0.05), "rango_si": [0.35, 0.65]}}


# ───────────────────────── criterios y evidencia de una aplicación ─────────────────────────
def antiguedad(fecha_aplicacion, fecha_ref: date) -> str:
    """Edad en meses = días / 30.44 (notebook 4.4). Sin fecha → se asume reciente."""
    try:
        f = datetime.strptime(str(fecha_aplicacion)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return "menos_1_anio"
    meses = (fecha_ref - f).days / 30.44
    return "menos_1_anio" if meses < 12 else "1_a_2_anios" if meses < 24 else "mas_2_anios"


def criterios(respuestas: dict, punt: dict, meta: dict, consistencia: dict, fecha_ref: date, total: int = 98) -> dict:
    respondidas = [v for v in respuestas.values() if v in (0, 1)]
    comp = len(respondidas) / total
    disp = dispersion_interes(punt)
    prop_si = sum(respondidas) / len(respondidas) if respondidas else 0.0
    lo, hi = consistencia["rango_si"]
    alerta = disp is not None and consistencia.get("disp_p05") is not None and disp < consistencia["disp_p05"] and lo <= prop_si <= hi
    modalidad = (meta.get("modalidad") or "supervisada").strip().lower().replace("ó", "o")
    return {"antiguedad": antiguedad(meta.get("fecha"), fecha_ref),
            "modalidad": modalidad if modalidad in ("supervisada", "autonoma") else "supervisada",
            "completitud": "completa" if comp >= 0.95 else "parcial" if comp >= 0.80 else "incompleta",
            "consistencia": "alerta" if alerta else "sin_alertas",
            "completitud_pct": round(comp * 100)}


def evidencia(respuestas: dict, meta: dict, calib: dict, claves, fecha_ref: date):
    """Una aplicación → (z por área, criterios, origen para la interfaz)."""
    respuestas = {int(k): normalizar_respuesta(v) for k, v in respuestas.items()}
    punt = puntajes(respuestas, claves)
    z = {}
    for a in CODIGOS:
        z[a] = {}
        for t in TIPOS_CHASIDE:
            m, sd = calib["normas_chaside"][a][t]
            z[a][t] = (punt[(a, t)] - m) / sd if punt[(a, t)] is not None and sd else None
    crit = criterios(respuestas, punt, meta, calib["consistencia"], fecha_ref, total=len(claves))
    esc = items_por_escala(claves)
    origen = {"respondidas": sum(1 for v in respuestas.values() if v in (0, 1)), "total": len(claves),
              "si": sum(1 for v in respuestas.values() if v == 1),
              "areas": {a: {t: [sum(1 for i in esc[(a, t)] if respuestas.get(i) == 1), len(esc[(a, t)])] for t in TIPOS_CHASIDE}
                        for a in CODIGOS}}
    return z, crit, origen
