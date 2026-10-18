"""Lectura de la configuración editable (carpeta config/): mapeo de materias, CHASIDE, fuentes y carreras."""
from __future__ import annotations

import csv
import io
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field

from .constantes import CODIGOS

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_CONFIG = os.environ.get("VOCACIONAL_CONFIG", os.path.join(RAIZ, "config"))


def _leer(ruta_o_texto: str) -> str:
    """Acepta una ruta a archivo o el contenido del CSV directamente."""
    if "\n" not in ruta_o_texto and os.path.exists(ruta_o_texto):
        with open(ruta_o_texto, encoding="utf-8-sig") as f:
            return f.read()
    return ruta_o_texto.lstrip("\ufeff")


# ───────────────────────── mapeo de materias ─────────────────────────
@dataclass
class Regla:
    indice: int
    patron: str
    incluir: str                 # 'si' | 'no'
    pesos: dict                  # {area: peso 0-3}
    justificacion: str
    regex: re.Pattern = field(repr=False, default=None)

    @property
    def areas(self) -> str:
        return "".join(a for a in CODIGOS if self.pesos.get(a, 0) > 0)


def cargar_mapeo(ruta: str | None = None) -> list[Regla]:
    """Reglas en orden de prioridad: gana la primera cuyo patrón (regex) aparece en el nombre de la materia."""
    texto = _leer(ruta or os.path.join(DIR_CONFIG, "mapeo_materias.csv"))
    reglas = []
    for i, r in enumerate(csv.DictReader(io.StringIO(texto))):
        pesos = {a: float(r.get(a) or 0) for a in CODIGOS}
        reglas.append(Regla(i, r["patron"], (r.get("incluir") or "").strip().lower(), pesos,
                            r.get("justificacion") or "", re.compile(r["patron"])))
    return reglas


def mapeo_a_csv(reglas: list[Regla]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["patron", "incluir"] + CODIGOS + ["justificacion"])
    for r in reglas:
        w.writerow([r.patron, r.incluir] + [int(r.pesos.get(a, 0)) for a in CODIGOS] + [r.justificacion])
    return out.getvalue()


def clasificar(materia: str, reglas: list[Regla]):
    """→ (Regla | None, estado) con estado 'incluida' | 'excluida' | 'sin_regla' (notebook 3.4)."""
    m = str(materia).lower().strip()
    for r in reglas:
        if r.regex.search(m):
            return r, ("incluida" if r.incluir == "si" else "excluida")
    return None, "sin_regla"


# ───────────────────────── CHASIDE ─────────────────────────
def cargar_claves(ruta: str | None = None) -> list[tuple[int, str, str]]:
    texto = _leer(ruta or os.path.join(DIR_CONFIG, "claves_chaside.csv"))
    claves = sorted((int(r["item"]), r["area"].strip(), r["tipo"].strip()) for r in csv.DictReader(io.StringIO(texto)))
    if len(claves) != 98 or sorted(c[0] for c in claves) != list(range(1, 99)):
        raise ValueError("claves_chaside.csv debe tener los ítems 1 a 98, cada uno una vez")
    return claves


def cargar_preguntas(ruta: str | None = None):
    ruta = ruta or os.path.join(DIR_CONFIG, "chaside_preguntas.csv")
    if not os.path.exists(ruta):
        return {}, "sin_texto"
    filas = list(csv.DictReader(io.StringIO(_leer(ruta))))
    preg = {int(r["item"]): r["texto"] for r in filas}
    origen = "prototipo" if any((r.get("origen") or "") == "prototipo" for r in filas) else "oficial"
    return preg, origen


def cargar_fuentes(ruta: str | None = None) -> dict:
    with open(ruta or os.path.join(DIR_CONFIG, "fuentes.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {x["id"]: x for x in d.get("nucleo", []) + d.get("complementarias", [])}


# ───────────────────────── carreras ─────────────────────────
def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def cargar_carreras(ruta: str | None = None):
    """Notebook 7.1: valida perfiles (1–5, no todo en 1) y genera ids únicos. → (lista, descartadas)."""
    texto = _leer(ruta or os.path.join(DIR_CONFIG, "carreras_EC.csv"))
    filas = list(csv.DictReader(io.StringIO(texto)))
    vistos, carreras, malas = {}, [], []
    for r in filas:
        r = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        nombre = r.get("Carrera universitaria") or r.get("nombre") or ""
        base = slug(nombre)
        n = vistos.get(base, 0); vistos[base] = n + 1
        cid = base if n == 0 else f"{base}-{n + 1}"
        try:
            perfil = {a: int(float(r[a])) for a in CODIGOS}
        except (KeyError, TypeError, ValueError):
            malas.append(nombre); continue
        if any(v not in (1, 2, 3, 4, 5) for v in perfil.values()) or all(v == 1 for v in perfil.values()):
            malas.append(nombre); continue
        hab = [r[k] for k in r if k.lower().startswith("habilidad") and r[k]]
        carreras.append({"id": cid, "nombre": nombre, "perfil": perfil, "habilidades": hab,
                         "universidad": r.get("Universidad") or r.get("universidad"),
                         "ciudad": r.get("Ciudad") or r.get("ciudad")})
    return carreras, malas
