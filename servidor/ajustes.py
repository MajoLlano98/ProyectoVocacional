"""Configuración del servidor desde variables de entorno (archivo .env en despliegue)."""
import os
import secrets

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bool(nombre, defecto):
    v = os.environ.get(nombre)
    return defecto if v is None else v.strip().lower() in ("1", "true", "si", "sí", "yes")


DATOS = os.environ.get("VOCACIONAL_DATOS", os.path.join(RAIZ, "datos"))
CONFIG_BASE = os.path.join(RAIZ, "config")            # valores de fábrica (en el repositorio)
CONFIG = os.path.join(DATOS, "config")                # copia editable del colegio (en el volumen de datos)
WEB = os.path.join(RAIZ, "web")
BD = os.path.join(DATOS, "vocacional.db")
RESPALDOS = os.path.join(DATOS, "respaldos")

NOMBRE_COLEGIO = os.environ.get("VOCACIONAL_COLEGIO", "Colegio")
COOKIE_SEGURA = _bool("VOCACIONAL_COOKIE_SEGURA", True)      # True detrás de HTTPS (Cloudflare)
HORAS_SESION = int(os.environ.get("VOCACIONAL_HORAS_SESION", "8"))
DIAS_CODIGO = int(os.environ.get("VOCACIONAL_DIAS_CODIGO", "30"))
RESPALDOS_CONSERVAR = int(os.environ.get("VOCACIONAL_RESPALDOS_CONSERVAR", "30"))
HORA_RESPALDO = int(os.environ.get("VOCACIONAL_HORA_RESPALDO", "2"))
HOSTS = [h.strip() for h in os.environ.get("VOCACIONAL_HOSTS", "*").split(",") if h.strip()]
MAX_ARCHIVO_MB = int(os.environ.get("VOCACIONAL_MAX_ARCHIVO_MB", "20"))


def secreto() -> str:
    """Clave para firmar sesiones y seudonimizar IDs. Debe venir del entorno en producción;
    en desarrollo se genera una y se guarda en datos/.secreto (¡respaldarla! sin ella no se reconocen los IDs)."""
    v = os.environ.get("VOCACIONAL_SECRETO")
    if v:
        if len(v) < 32:
            raise RuntimeError("VOCACIONAL_SECRETO debe tener al menos 32 caracteres")
        return v
    os.makedirs(DATOS, exist_ok=True)
    ruta = os.path.join(DATOS, ".secreto")
    if not os.path.exists(ruta):
        with open(ruta, "w") as f:
            f.write(secrets.token_urlsafe(48))
        os.chmod(ruta, 0o600)
    with open(ruta) as f:
        return f.read().strip()
