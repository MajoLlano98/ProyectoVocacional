"""Base de datos SQLite (un solo archivo en datos/vocacional.db, modo WAL)."""
from __future__ import annotations

import contextvars
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from . import ajustes

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY, usuario TEXT UNIQUE NOT NULL COLLATE NOCASE, nombre TEXT NOT NULL,
  rol TEXT NOT NULL CHECK (rol IN ('admin','orientador')), hash TEXT NOT NULL,
  activo INTEGER NOT NULL DEFAULT 1, version_sesion INTEGER NOT NULL DEFAULT 1,
  creado TEXT NOT NULL, ultimo_acceso TEXT);

CREATE TABLE IF NOT EXISTS estudiantes (
  id TEXT PRIMARY KEY,                      -- seudónimo E-xxxxxx (lo único que ve la interfaz)
  id_colegio_hmac TEXT UNIQUE NOT NULL,     -- HMAC del ID del sistema académico: permite cruzar entregas sin guardarlo
  nombre TEXT NOT NULL, genero TEXT, nombre_ficticio INTEGER NOT NULL DEFAULT 1,
  grado_actual INTEGER, paralelo TEXT, activo INTEGER NOT NULL DEFAULT 1,
  creado TEXT NOT NULL, actualizado TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS calificaciones (
  estudiante_id TEXT NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
  anio TEXT NOT NULL, grado INTEGER, materia TEXT NOT NULL, nota REAL, letra TEXT,
  carga_id INTEGER, PRIMARY KEY (estudiante_id, anio, grado, materia));

CREATE TABLE IF NOT EXISTS chaside (
  id INTEGER PRIMARY KEY, estudiante_id TEXT NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
  fecha TEXT NOT NULL, modalidad TEXT NOT NULL, respuestas TEXT NOT NULL,
  origen TEXT NOT NULL,                     -- en_linea | dece | archivo
  registrado_por TEXT, creado TEXT NOT NULL, anulado INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_chaside_est ON chaside(estudiante_id, anulado, fecha);

CREATE TABLE IF NOT EXISTS codigos (
  id INTEGER PRIMARY KEY, estudiante_id TEXT NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
  hash TEXT UNIQUE NOT NULL, modalidad TEXT NOT NULL, creado_por TEXT, creado TEXT NOT NULL,
  expira TEXT NOT NULL, usado TEXT, intentos INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS resultados (
  estudiante_id TEXT PRIMARY KEY REFERENCES estudiantes(id) ON DELETE CASCADE,
  json TEXT NOT NULL, indice TEXT NOT NULL, calibracion_id INTEGER, generado TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS calibraciones (
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, json TEXT NOT NULL, activa INTEGER NOT NULL DEFAULT 0,
  usuario TEXT, resumen TEXT);

CREATE TABLE IF NOT EXISTS cargas (
  id INTEGER PRIMARY KEY, tipo TEXT NOT NULL, archivo TEXT, sha256 TEXT, usuario TEXT, fecha TEXT NOT NULL, resumen TEXT);

CREATE TABLE IF NOT EXISTS trabajos (
  id INTEGER PRIMARY KEY, tipo TEXT NOT NULL, estado TEXT NOT NULL, progreso REAL NOT NULL DEFAULT 0,
  mensaje TEXT, usuario TEXT, creado TEXT NOT NULL, terminado TEXT);

CREATE TABLE IF NOT EXISTS auditoria (
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, usuario TEXT, ip TEXT, accion TEXT NOT NULL, objeto TEXT, detalle TEXT);
CREATE INDEX IF NOT EXISTS ix_auditoria_fecha ON auditoria(fecha);

CREATE TABLE IF NOT EXISTS ajustes (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
"""

_local = threading.local()
IP_ACTUAL = contextvars.ContextVar("ip_actual", default=None)      # la fija el middleware en cada solicitud
_escritura = threading.RLock()


def ahora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def conexion() -> sqlite3.Connection:
    c = getattr(_local, "c", None)
    if c is None:
        os.makedirs(ajustes.DATOS, exist_ok=True)
        c = sqlite3.connect(ajustes.BD, timeout=30, isolation_level=None, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=30000")
        _local.c = c
    return c


def iniciar():
    c = conexion()
    c.executescript(ESQUEMA)
    try:
        os.chmod(ajustes.BD, 0o600)
    except OSError:
        pass


@contextmanager
def transaccion():
    """Escrituras serializadas (SQLite admite un escritor a la vez)."""
    with _escritura:
        c = conexion()
        nivel = getattr(_local, "nivel", 0)
        if nivel:                                   # transacción anidada: se integra en la externa
            _local.nivel = nivel + 1
            try:
                yield c
            finally:
                _local.nivel = nivel
            return
        _local.nivel = 1
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise
        finally:
            _local.nivel = 0


def uno(sql, *p):
    r = conexion().execute(sql, p).fetchone()
    return dict(r) if r else None


def todos(sql, *p):
    return [dict(r) for r in conexion().execute(sql, p).fetchall()]


def ajuste(clave, defecto=None):
    r = uno("SELECT valor FROM ajustes WHERE clave=?", clave)
    return json.loads(r["valor"]) if r else defecto


def fijar_ajuste(clave, valor):
    with transaccion() as c:
        c.execute("INSERT INTO ajustes(clave, valor) VALUES(?, ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
                  (clave, json.dumps(valor, ensure_ascii=False)))


def auditar(usuario, ip, accion, objeto=None, detalle=None):
    with transaccion() as c:
        c.execute("INSERT INTO auditoria(fecha, usuario, ip, accion, objeto, detalle) VALUES (?,?,?,?,?,?)",
                  (ahora(), usuario, ip or IP_ACTUAL.get(), accion, objeto,
                   json.dumps(detalle, ensure_ascii=False) if isinstance(detalle, (dict, list)) else detalle))
