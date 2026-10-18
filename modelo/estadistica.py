"""Funciones numéricas compartidas (sin dependencias pesadas)."""
from __future__ import annotations

import math

import numpy as np

SQRT2 = math.sqrt(2.0)


def phi(z: float) -> float:
    """Φ(z), distribución normal estándar acumulada."""
    return 0.5 * (1.0 + math.erf(z / SQRT2))


try:                                   # scipy es rápido; si no está, se usa math.erf vectorizada
    from scipy.special import ndtr as _ndtr
except ImportError:                    # pragma: no cover
    _erf_np = np.vectorize(math.erf, otypes=[float])

    def _ndtr(z):
        return 0.5 * (1.0 + _erf_np(np.asarray(z, dtype=float) / SQRT2))


def phi_np(z):
    """Φ vectorizada sobre arreglos de numpy."""
    return _ndtr(np.asarray(z, dtype=float))


def percentil(z: float) -> int:
    return round(phi(z) * 100)


def media_sd(valores):
    """Media y desviación muestral (ddof=1) ignorando None/NaN — igual que pandas."""
    v = [x for x in valores if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n == 0:
        return None, None, 0
    m = sum(v) / n
    if n < 2:
        return m, None, n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    return m, sd, n


def cuantil(valores, q: float):
    """Cuantil con interpolación lineal (pandas/numpy por defecto)."""
    v = sorted(x for x in valores if x is not None and not math.isnan(x))
    if not v:
        return None
    return float(np.quantile(np.array(v), q))


def bvnu(h: float, k: float, r: float) -> float:
    """P(X > h, Y > k) para normal bivariada estándar con correlación r (algoritmo de Genz, igual que motor.js)."""
    tp = 2 * math.pi
    if abs(r) < 0.3:
        w = [0.1713244923791705, 0.3607615730481384, 0.4679139345726904]
        x = [0.9324695142031522, 0.6612093864662647, 0.2386191860831970]
    elif abs(r) < 0.75:
        w = [0.04717533638651177, 0.1069393259953183, 0.1600783285433464, 0.2031674267230659, 0.2334925365383547, 0.2491470458134029]
        x = [0.9815606342467191, 0.9041172563704750, 0.7699026741943050, 0.5873179542866171, 0.3678314989981802, 0.1252334085114692]
    else:
        w = [0.01761400713915212, 0.04060142980038694, 0.06267204833410906, 0.08327674157670475, 0.1019301198172404,
             0.1181945319615184, 0.1316886384491766, 0.1420961093183821, 0.1491729864726037, 0.1527533871307259]
        x = [0.9931285991850949, 0.9639719272779138, 0.9122344282513259, 0.8391169718222188, 0.7463319064601508,
             0.6360536807265150, 0.5108670019508271, 0.3737060887154196, 0.2277858511416451, 0.07652652113349733]
    hk = h * k
    bvn = 0.0
    if abs(r) < 0.925:
        hs = (h * h + k * k) / 2
        asr = math.asin(r) / 2
        for wi, xi in zip(w, x):
            sn = math.sin(asr * (1 - xi)); bvn += wi * math.exp((sn * hk - hs) / (1 - sn * sn))
            sn = math.sin(asr * (1 + xi)); bvn += wi * math.exp((sn * hk - hs) / (1 - sn * sn))
        bvn = bvn * asr / tp + phi(-h) * phi(-k)
    else:
        if r < 0:
            k, hk = -k, -hk
        if abs(r) < 1:
            as_ = (1 - r) * (1 + r); a = math.sqrt(as_)
            bs = (h - k) ** 2; c = (4 - hk) / 8; d = (12 - hk) / 16
            bvn = a * math.exp(-(bs / as_ + hk) / 2) * (1 - c * (bs - as_) * (1 - d * bs / 5) / 3 + c * d * as_ * as_ / 5)
            if hk > -160:
                b = math.sqrt(bs)
                bvn -= math.exp(-hk / 2) * math.sqrt(tp) * phi(-b / a) * b * (1 - c * bs * (1 - d * bs / 5) / 3)
            a /= 2
            for wi, xi in zip(w, x):
                for sg in (-1, 1):
                    xs = (a * (sg * xi + 1)) ** 2; rs = math.sqrt(1 - xs); asr = -(bs / xs + hk) / 2
                    if asr > -100:
                        bvn += a * wi * math.exp(asr) * (math.exp(-hk * xs / (2 * (1 + rs) ** 2)) / rs - (1 + c * xs * (1 + d * xs)))
            bvn = -bvn / tp
        if r > 0:
            bvn += phi(-max(h, k))
        elif h >= k:
            bvn = -bvn
        else:
            bvn = (phi(k) - phi(h) if h < 0 else phi(-h) - phi(-k)) - bvn
    return max(0.0, min(1.0, bvn))


class RNG:
    """mulberry32 + Box–Muller: misma secuencia que motor.js, para que servidor y navegador coincidan."""

    def __init__(self, semilla: int):
        self.a = semilla & 0xFFFFFFFF

    def _u(self) -> float:
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    def normal(self) -> float:
        u1 = self._u(); u2 = self._u()
        return math.sqrt(-2 * math.log(u1 + 1e-12)) * math.cos(2 * math.pi * u2)

    def normales(self, n: int):
        return np.fromiter((self.normal() for _ in range(n)), dtype=float, count=n)


def corr_pareada(x, y):
    """Correlación de Pearson con pares completos (como pandas .corr)."""
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < 2:
        return float("nan")
    xs, ys = x[m], y[m]
    sx, sy = xs.std(ddof=1), ys.std(ddof=1)
    if sx == 0 or sy == 0:
        return float("nan")
    return float(((xs - xs.mean()) * (ys - ys.mean())).sum() / ((len(xs) - 1) * sx * sy))
