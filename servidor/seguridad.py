"""Contraseñas, seudónimos, códigos de acceso, límites de intentos y cabeceras de seguridad."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

from . import ajustes

# ───────────────────────── contraseñas (scrypt, biblioteca estándar) ─────────────────────────
_N, _R, _P = 2 ** 14, 8, 1


def hash_clave(clave: str) -> str:
    sal = secrets.token_bytes(16)
    d = hashlib.scrypt(clave.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${base64.b64encode(sal).decode()}${base64.b64encode(d).decode()}"


def verificar_clave(clave: str, guardado: str) -> bool:
    try:
        _, n, r, p, sal, d = guardado.split("$")
        calc = hashlib.scrypt(clave.encode(), salt=base64.b64decode(sal), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(d))
    except (ValueError, TypeError):
        return False


# Hash ficticio para igualar el tiempo de respuesta cuando el usuario no existe
HASH_FICTICIO = hash_clave(secrets.token_urlsafe(16))


def validar_clave_nueva(clave: str) -> str | None:
    if len(clave) < 10:
        return "La contraseña debe tener al menos 10 caracteres."
    if clave.lower() == clave or clave.upper() == clave or not any(ch.isdigit() for ch in clave):
        return "La contraseña debe combinar mayúsculas, minúsculas y números."
    return None


# ───────────────────────── seudónimos ─────────────────────────
def hmac_id(id_colegio: str) -> str:
    """El ID del sistema académico nunca se guarda: solo su HMAC con el secreto del servidor."""
    return hmac.new(ajustes.secreto().encode(), str(id_colegio).strip().encode(), hashlib.sha256).hexdigest()


def nuevo_id_estudiante() -> str:
    return f"E-{secrets.token_hex(3)}"


# ───────────────────────── códigos de acceso al CHASIDE ─────────────────────────
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"        # sin 0/O, 1/I para dictarlos sin errores


def nuevo_codigo() -> str:
    c = "".join(secrets.choice(ALFABETO) for _ in range(8))
    return f"{c[:4]}-{c[4:]}"


def normalizar_codigo(c: str) -> str:
    c = "".join(ch for ch in str(c).upper() if ch in ALFABETO)
    return f"{c[:4]}-{c[4:8]}" if len(c) == 8 else ""


def hash_codigo(c: str) -> str:
    return hmac.new(ajustes.secreto().encode(), b"codigo:" + normalizar_codigo(c).encode(), hashlib.sha256).hexdigest()


# ───────────────────────── límite de intentos (en memoria) ─────────────────────────
class Limitador:
    """Máximo `n` intentos fallidos por clave en `ventana` segundos."""

    def __init__(self, n: int, ventana: int):
        self.n, self.ventana = n, ventana
        self._f = defaultdict(deque)
        self._lock = threading.Lock()

    def bloqueado(self, clave: str) -> bool:
        with self._lock:
            q = self._f[clave]
            ahora = time.monotonic()
            while q and ahora - q[0] > self.ventana:
                q.popleft()
            return len(q) >= self.n

    def fallo(self, clave: str):
        with self._lock:
            self._f[clave].append(time.monotonic())

    def limpiar(self, clave: str):
        with self._lock:
            self._f.pop(clave, None)


LOGIN = Limitador(5, 15 * 60)            # 5 fallos / 15 min por usuario+IP
CODIGO = Limitador(10, 15 * 60)          # 10 códigos inválidos / 15 min por IP

# ───────────────────────── cabeceras ─────────────────────────
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
CABECERAS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def ip_cliente(request) -> str:
    """Detrás de Cloudflare Tunnel la IP real viene en CF-Connecting-IP."""
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
