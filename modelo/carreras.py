"""
Módulo 7 · Carreras: afinidad equilibrada, P(top 5) por Monte Carlo y razones (notebook 7.2–7.3).
"""
from __future__ import annotations

import numpy as np

from .constantes import (BETA_INTERES, CODIGOS, EJES, GAMMAS_CANDIDATOS, N_EXPORTAR, N_SIM, SEMILLA_MC, TOP_K,
                         TV_MAX)
from .estadistica import RNG, phi_np


def matriz_perfil(carreras: list[dict]) -> np.ndarray:
    return np.array([[c["perfil"][a] for a in CODIGOS] for c in carreras], dtype=float)


def pesos_carrera(perfil: np.ndarray, gamma: float) -> np.ndarray:
    W = ((perfil - 1) / 4) ** gamma
    return W / W.sum(axis=1, keepdims=True)


def afinidad_cruda(MU: np.ndarray, WN: np.ndarray, beta: float = BETA_INTERES) -> np.ndarray:
    """MU: (..., 7, 2) → (..., carreras) en 0–100."""
    s = beta * phi_np(MU[..., 0]) + (1 - beta) * phi_np(MU[..., 1])
    return 100 * s @ WN.T


def ajustar_normas(MUs: list[np.ndarray], WN: np.ndarray, betas=None) -> dict:
    betas = np.round(np.arange(0, 1.01, 0.1), 1) if betas is None else betas
    out = {}
    for b in betas:
        A = np.array([afinidad_cruda(MU, WN, float(b)) for MU in MUs])
        out[f"{b:.1f}"] = {"media": A.mean(axis=0).tolist(), "sd": A.std(axis=0, ddof=1).tolist()}
    return out


def afinidad(MU: np.ndarray, WN: np.ndarray, normas: dict, beta: float = BETA_INTERES) -> np.ndarray:
    """Afinidad equilibrada: percentil del estudiante en la cohorte para cada carrera."""
    n = normas[f"{beta:.1f}"]
    return 100 * phi_np((afinidad_cruda(MU, WN, beta) - np.array(n["media"])) / np.array(n["sd"]))


def elegir_gamma(MUs: list[np.ndarray], perfil: np.ndarray, beta: float = BETA_INTERES,
                 candidatos=GAMMAS_CANDIDATOS, tv_max: float = TV_MAX):
    """γ más bajo cuyo reparto del área de la carrera #1 se parece al área más fuerte de los estudiantes (TV ≤ 0.10)."""
    S = np.array([beta * phi_np(MU[:, 0]) + (1 - beta) * phi_np(MU[:, 1]) for MU in MUs])
    fuerte = np.bincount(S.argmax(1), minlength=7) / len(S)
    principal = perfil.argmax(1)
    tabla = []
    for g in candidatos:
        X = S @ pesos_carrera(perfil, g).T
        Z = (X - X.mean(0)) / X.std(0, ddof=1)
        uno = principal[Z.argmax(1)]
        tv = 0.5 * np.abs(np.bincount(uno, minlength=7) / len(S) - fuerte).sum()
        tabla.append({"gamma": g, "tv": float(tv), "en_area_fuerte": float(np.mean(uno == S.argmax(1)))})
    ok = [t["gamma"] for t in tabla if t["tv"] <= tv_max]
    return (float(ok[0]) if ok else float(min(tabla, key=lambda t: t["tv"])["gamma"])), tabla


def monte_carlo(MU: np.ndarray, SIG: np.ndarray, WN: np.ndarray, normas: dict, beta: float = BETA_INTERES,
                n: int = N_SIM, k: int = TOP_K, semilla: int = SEMILLA_MC):
    """Sorteos del posterior → P(top k) y rango 90 % de la afinidad (misma secuencia aleatoria que motor.js)."""
    na = MU.shape[0]
    eps = RNG(semilla).normales(n * na * 2).reshape(n, na, 2)
    L = np.zeros((na, 3))
    for a in range(na):
        l00 = np.sqrt(SIG[a][0][0]); l10 = SIG[a][1][0] / l00
        L[a] = (l00, l10, np.sqrt(max(1e-12, SIG[a][1][1] - l10 * l10)))
    di = MU[:, 0] + L[:, 0] * eps[:, :, 0]
    dr = MU[:, 1] + L[:, 1] * eps[:, :, 0] + L[:, 2] * eps[:, :, 1]
    A = afinidad(np.stack([di, dr], axis=-1), WN, normas, beta)
    top = np.argsort(-A, axis=1, kind="stable")[:, :k]
    p = np.bincount(top.ravel(), minlength=A.shape[1]) / n
    As = np.sort(A, axis=0)
    lo = As[min(n - 1, int(0.05 * n))]; hi = As[min(n - 1, int(0.95 * n))]
    return p, lo, hi


def razon(areas: list[dict], carrera: dict, wn_fila: np.ndarray, MU: np.ndarray, beta: float = BETA_INTERES) -> str:
    s = beta * phi_np(MU[:, 0]) + (1 - beta) * phi_np(MU[:, 1])
    ap = wn_fila * s
    orden = np.argsort(-ap, kind="stable")
    a = areas[orden[0]]
    pI, pR = a["interes"]["percentil"], a["rendimiento"]["percentil"]
    txt = f"{EJES[a['codigo']]} (pesa {int(carrera['perfil'][a['codigo']])}/5 en la carrera): interés P{pI}, rendimiento P{pR}"
    mats = [f"{m['materia']} {m['nota']:.1f}" for m in a.get("materias_clave", []) if m.get("nota") is not None]
    if mats:
        txt += " · materias: " + ", ".join(mats)
    if pI >= 60 and pR < 40:
        txt += " · interés alto, conviene reforzar el rendimiento"
    elif pR >= 60 and pI < 40:
        txt += " · rinde bien aunque declara poco interés"
    if ap[orden[1]] >= 0.5 * ap[orden[0]]:
        txt += f" · también suma {EJES[areas[orden[1]]['codigo']]}"
    return txt


def ranking(areas: list[dict], MU: np.ndarray, SIG: np.ndarray, carreras: list[dict], calib_carreras: dict,
            beta: float = BETA_INTERES, n_sim: int = N_SIM, top_k: int = TOP_K, n_exportar: int = N_EXPORTAR):
    perfil = matriz_perfil(carreras)
    WN = pesos_carrera(perfil, calib_carreras["gamma"])
    A = afinidad(MU, WN, calib_carreras["normas"], beta)
    p, lo, hi = monte_carlo(MU, SIG, WN, calib_carreras["normas"], beta, n_sim, top_k)
    orden = np.argsort(-A, kind="stable")[:n_exportar]
    return [{"id": carreras[j]["id"], "nombre": carreras[j]["nombre"], "afinidad": round(float(A[j]), 1),
             "rango90": [round(float(lo[j]), 1), round(float(hi[j]), 1)], "p_top5": round(float(p[j]), 2),
             "universidad": carreras[j].get("universidad"), "ciudad": carreras[j].get("ciudad"),
             "razon": razon(areas, carreras[j], WN[j], MU, beta)} for j in orden]
