"""Respaldo diario de la base de datos (API de backup de SQLite: copia consistente sin detener el servicio)."""
from __future__ import annotations

import glob
import os
import shutil
import sqlite3
import threading
import time
import traceback
from datetime import datetime

from . import ajustes, bd


def respaldar(motivo: str = "manual") -> str:
    os.makedirs(ajustes.RESPALDOS, exist_ok=True)
    destino = os.path.join(ajustes.RESPALDOS, f"vocacional_{datetime.now():%Y%m%d-%H%M%S}_{motivo}.db")
    origen = sqlite3.connect(ajustes.BD)
    copia = sqlite3.connect(destino)
    with copia:
        origen.backup(copia)
    copia.close(); origen.close()
    os.chmod(destino, 0o600)
    # la configuración editable y el secreto también se guardan (sin el secreto no se reconocen los IDs del colegio)
    carpeta_cfg = destino[:-3] + "_config"
    shutil.copytree(ajustes.CONFIG, carpeta_cfg, dirs_exist_ok=True)
    rotar()
    return destino


def rotar():
    archivos = sorted(glob.glob(os.path.join(ajustes.RESPALDOS, "vocacional_*.db")))
    for viejo in archivos[:-ajustes.RESPALDOS_CONSERVAR]:
        os.remove(viejo)
        shutil.rmtree(viejo[:-3] + "_config", ignore_errors=True)


def lista():
    return [{"archivo": os.path.basename(p), "bytes": os.path.getsize(p), "fecha": datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec="seconds")}
            for p in sorted(glob.glob(os.path.join(ajustes.RESPALDOS, "vocacional_*.db")), reverse=True)]


def programar(tarea_nocturna=None):
    """Hilo que una vez al día respalda la base y ejecuta la tarea nocturna (recalcular antigüedad del CHASIDE)."""
    def bucle():
        ultimo = None
        while True:
            try:
                hoy = datetime.now()
                if hoy.hour == ajustes.HORA_RESPALDO and ultimo != hoy.date():
                    ultimo = hoy.date()
                    respaldar("diario")
                    bd.auditar("sistema", None, "respaldo_diario")
                    if tarea_nocturna:
                        tarea_nocturna()
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            time.sleep(300)
    threading.Thread(target=bucle, daemon=True, name="respaldo-diario").start()
