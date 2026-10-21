"""
Módulo 5 · Modelo bayesiano Interés × Rendimiento por área.

  · posterior gaussiano exacto (notebook 5.3, modo «aprendido»)
  · probabilidades de cuadrante y zona con umbral de certeza
  · aprendizaje de parámetros con partición 70/30 (notebook 5.2)
"""
from __future__ import annotations

import math

import numpy as np

from .constantes import (CODIGOS, FRACCION_ENTRENAMIENTO, OBJETIVO_EXACTITUD_ZONA, RUBRICA, SEMILLA_PARTICION, TEXTO_AUTO,
                         TEXTO_ZONA, UMBRAL_CERTEZA, UMBRALES_CANDIDATOS)
from .estadistica import bvnu, corr_pareada, media_sd, phi

CRITERIOS_APLICACION = ("antiguedad", "modalidad", "completitud", "consistencia")


def sigma2(alfa: float, criterios: dict, rubrica: dict = RUBRICA) -> float:
    """Varianza efectiva de una fuente: (1-α)/α × producto de factores de la rúbrica (notebook 1.5)."""
    f = 1.0
    for c, nivel in criterios.items():
        if nivel is not None and c in rubrica:
            f *= rubrica[c][nivel]
    return (1 - alfa) / alfa * f


def posterior_area(ev: dict, p: dict, alfa_int: float | None, crit: dict, fuentes: dict | None = None,
                   rubrica: dict = RUBRICA):
    """ev: {z_int, z_apt, z_notas, W_efectiva}. Devuelve (mu[2], Sigma[2x2], aportes)."""
    fuentes = fuentes or {}
    rho = p["rho"]
    det = 1 - rho * rho
    L = np.array([[1 / det, -rho / det], [-rho / det, 1 / det]])
    b = np.zeros(2)
    crit_ap = {k: crit.get(k) for k in CRITERIOS_APLICACION if crit.get(k)}
    obs = []
    if ev.get("z_int") is not None and alfa_int:
        c_f = (fuentes.get("chaside_int") or {}).get("criterios", {"validacion": "publicada", "equivalencia": "directa"})
        obs.append(("chaside_interes", np.array([1.0, 0.0]), ev["z_int"] / math.sqrt(alfa_int),
                    sigma2(alfa_int, {**c_f, **crit_ap}, rubrica)))
    if ev.get("z_notas") is not None:
        an = p["alfa_notas"]
        f_w = float(np.clip(p["W_med"] / ev["W_efectiva"], 0.5, 3.0)) if ev.get("W_efectiva") else 1.0
        # α aprendido ya incorpora la validez → criterios de notas: publicada/directa (factor 1)
        obs.append(("notas", np.array([0.0, 1.0]), ev["z_notas"] / math.sqrt(an), sigma2(an, {}, rubrica) * f_w))
    if ev.get("z_apt") is not None:
        lam = p["lam_apt"]
        c_f = (fuentes.get("chaside_apt") or {}).get("criterios", {"validacion": "publicada", "equivalencia": "directa"})
        obs.append(("autopercepcion", np.array([0.0, 1.0]), ev["z_apt"] / lam, sigma2(lam * lam, {**c_f, **crit_ap}, rubrica)))
    for _, H, y, s2 in obs:
        L = L + np.outer(H, H) / s2
        b = b + H * y / s2
    S = np.linalg.inv(L)
    mu = S @ b
    aportes = {n: S @ (H * y / s2) for n, H, y, s2 in obs}
    return mu, S, aportes


def zona(mu, S, umbral: float = UMBRAL_CERTEZA) -> dict:
    sI, sR = math.sqrt(S[0][0]), math.sqrt(S[1][1])
    pI, pR = phi(mu[0] / sI), phi(mu[1] / sR)
    pAA = bvnu(-mu[0] / sI, -mu[1] / sR, S[0][1] / (sI * sR))
    probs = {"vocacion_consolidada": pAA, "interes_a_fortalecer": pI - pAA,
             "talento_no_explorado": pR - pAA, "no_prioritaria": 1 - pI - pR + pAA}
    mejor = max(probs, key=probs.get)
    clave = mejor if probs[mejor] >= umbral else "indeterminado"
    return {"clave": clave, "texto": TEXTO_ZONA[clave], "certeza": probs[mejor], "probabilidades": probs}


def elegir_umbral(certezas, objetivo: float = OBJETIVO_EXACTITUD_ZONA, candidatos=UMBRALES_CANDIDATOS) -> dict:
    """v1.1 · umbral de certeza SIN etiquetas.

    certezas = probabilidad de la zona más probable de cada estudiante×área de la cohorte. Como el posterior es
    probabilístico, la media de esas probabilidades entre las áreas decididas ES la exactitud que el modelo espera.
    Se elige el menor umbral cuya exactitud esperada alcanza el objetivo (más bajo = menos «indeterminados»).
    """
    p = np.asarray([c for c in certezas if c is not None], float)
    if p.size == 0:
        return {"umbral": UMBRAL_CERTEZA, "exactitud_esperada": None, "indeterminados": None, "objetivo": objetivo}
    for u in candidatos:
        dec = p >= u
        if dec.any() and p[dec].mean() >= objetivo:
            break
    dec = p >= u
    return {"umbral": float(u), "exactitud_esperada": float(p[dec].mean()) if dec.any() else None,
            "indeterminados": float(1 - dec.mean()), "objetivo": objetivo}


def autopercepcion(z_apt, z_notas, r_apt_notas):
    if z_apt is None or z_notas is None:
        return None
    br = (z_apt - r_apt_notas * z_notas) / math.sqrt(1 - r_apt_notas ** 2)
    k = "por_encima" if br > 1 else "por_debajo" if br < -1 else "coherente"
    return {"clave": k, "texto": TEXTO_AUTO[k]}


def eje(mu: float, sd: float) -> dict:
    return {"percentil": round(phi(mu) * 100), "rango90": [round(phi(mu - 1.645 * sd) * 100), round(phi(mu + 1.645 * sd) * 100)],
            "z": mu, "sd": sd}


# ───────────────────────── 5.2 aprendizaje ─────────────────────────
def particion(ids, semilla: int = SEMILLA_PARTICION):
    arr = np.array(sorted(ids))
    np.random.default_rng(semilla).shuffle(arr)
    k = int(FRACCION_ENTRENAMIENTO * len(arr))
    return set(arr[:k].tolist()), set(arr[k:].tolist())


def aprender(ev: dict, train: set, alfa_chaside: dict, alfa_notas: dict) -> dict:
    """ev: {id: {area: {z_int, z_apt, z_notas, W_efectiva}}} (solo estudiantes con núcleo completo)."""
    P = {}
    for a in CODIGOS:
        filas = [ev[i][a] for i in train if i in ev]
        filas = [f for f in filas if None not in (f.get("z_int"), f.get("z_apt"), f.get("z_notas"))]
        an, ai = alfa_notas[a], alfa_chaside[a]["interes"]
        zi = [f["z_int"] for f in filas]; za = [f["z_apt"] for f in filas]; zn = [f["z_notas"] for f in filas]
        r_an, r_in = corr_pareada(za, zn), corr_pareada(zi, zn)
        lam = float(np.clip(r_an / math.sqrt(an), 0.10, 0.90))
        W = [ev[i][a].get("W_efectiva") for i in ev]
        W = sorted(w for w in W if w is not None)
        P[a] = {"alfa_notas": an, "lam_apt": lam, "r_apt_notas": r_an,
                "rho": float(np.clip(r_in / math.sqrt(ai * an), -0.9, 0.9)),
                "W_med": float(np.median(W)) if W else None}
    return P


def resumen_parametros(P: dict, alfa_chaside: dict) -> dict:
    return {a: {"KR20 interés": alfa_chaside[a]["interes"], "α notas": P[a]["alfa_notas"],
                "λ² autopercepción": P[a]["lam_apt"] ** 2, "ρ interés–rendimiento": P[a]["rho"]} for a in CODIGOS}


__all__ = ["posterior_area", "zona", "elegir_umbral", "autopercepcion", "eje", "particion", "aprender", "media_sd"]
