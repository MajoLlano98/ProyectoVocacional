"""
Lógica del sistema: importar datos del colegio, registrar CHASIDE, calcular resultados y recalibrar.
Todo pasa por aquí; las rutas HTTP (app.py) solo validan permisos y formato.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import threading
import traceback
from datetime import date, datetime, timedelta

from modelo import calibracion as mcal, chaside as mch, configuracion as cfg, notas as mnotas, resultado as mres
from modelo.nombres import nombre_ficticio

from . import ajustes, bd, seguridad

ARCHIVOS_CONFIG = ["mapeo_materias.csv", "claves_chaside.csv", "chaside_preguntas.csv", "fuentes.json", "carreras_EC.csv"]
_cache = {"config": None, "config_mtime": None, "calib": None, "calib_id": None, "cohorte": None, "version": 0}
_lock_cache = threading.RLock()
_lock_trabajo = threading.Lock()


class ErrorUsuario(Exception):
    """Error que se muestra tal cual a quien usa la aplicación."""


# ───────────────────────── configuración editable ─────────────────────────
def preparar_config():
    """Primera vez: copia la configuración de fábrica al volumen de datos, donde el colegio puede editarla."""
    os.makedirs(ajustes.CONFIG, exist_ok=True)
    for n in ARCHIVOS_CONFIG:
        if not os.path.exists(os.path.join(ajustes.CONFIG, n)):
            shutil.copy(os.path.join(ajustes.CONFIG_BASE, n), os.path.join(ajustes.CONFIG, n))


def config():
    with _lock_cache:
        mt = tuple(os.path.getmtime(os.path.join(ajustes.CONFIG, n)) for n in ARCHIVOS_CONFIG)
        if _cache["config"] is None or _cache["config_mtime"] != mt:
            c = ajustes.CONFIG
            carreras, malas = cfg.cargar_carreras(os.path.join(c, "carreras_EC.csv"))
            preguntas, origen = cfg.cargar_preguntas(os.path.join(c, "chaside_preguntas.csv"))
            _cache["config"] = {"reglas": cfg.cargar_mapeo(os.path.join(c, "mapeo_materias.csv")),
                                "claves": cfg.cargar_claves(os.path.join(c, "claves_chaside.csv")),
                                "preguntas": preguntas, "preguntas_origen": origen,
                                "fuentes": cfg.cargar_fuentes(os.path.join(c, "fuentes.json")),
                                "carreras": carreras, "carreras_descartadas": malas}
            _cache["config_mtime"] = mt
            _cache["calib"] = None
            _cache["cohorte"] = None
        return _cache["config"]


def guardar_mapeo(reglas_json: list[dict], usuario: str):
    """Reemplaza las reglas de materias (validando cada patrón) y recalcula a todos."""
    import re
    filas = []
    for i, r in enumerate(reglas_json):
        patron = str(r.get("patron", "")).strip()
        if not patron:
            raise ErrorUsuario(f"La regla {i + 1} no tiene patrón.")
        try:
            re.compile(patron)
        except re.error as e:
            raise ErrorUsuario(f"El patrón de la regla {i + 1} no es válido: {e}")
        incluir = "si" if str(r.get("incluir", "si")).lower() in ("si", "sí", "true", "1") else "no"
        pesos = {}
        for a in cfg.CODIGOS:
            try:
                w = int(float(r.get("pesos", {}).get(a, 0) or 0))
            except (TypeError, ValueError):
                raise ErrorUsuario(f"Regla {i + 1}: el peso de {a} debe ser un número de 0 a 3.")
            if not 0 <= w <= 3:
                raise ErrorUsuario(f"Regla {i + 1}: el peso de {a} debe estar entre 0 y 3.")
            pesos[a] = w if incluir == "si" else 0
        if incluir == "si" and not any(pesos.values()):
            raise ErrorUsuario(f"Regla {i + 1}: una materia incluida debe aportar al menos a un área.")
        filas.append(cfg.Regla(i, patron, incluir, pesos, str(r.get("justificacion", "")).strip()))
    ruta = os.path.join(ajustes.CONFIG, "mapeo_materias.csv")
    shutil.copy(ruta, ruta + f".{datetime.now():%Y%m%d-%H%M%S}.bak")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(cfg.mapeo_a_csv(filas))
    config()
    bd.auditar(usuario, None, "editar_mapeo_materias", detalle={"reglas": len(filas)})
    return lanzar_trabajo("recalcular", usuario, lambda t: recalcular(None, t))


# ───────────────────────── calibración ─────────────────────────
def calibracion_activa():
    with _lock_cache:
        if _cache["calib"] is not None:
            return _cache["calib"], _cache["calib_id"]
        fila = bd.uno("SELECT id, json FROM calibraciones WHERE activa=1 ORDER BY id DESC LIMIT 1")
        if not fila:
            with open(os.path.join(ajustes.CONFIG_BASE, "calibracion_referencia.json"), encoding="utf-8") as f:
                ref = json.load(f)
            with bd.transaccion() as c:
                cur = c.execute("INSERT INTO calibraciones(fecha, json, activa, usuario, resumen) VALUES (?,?,1,?,?)",
                                (bd.ahora(), json.dumps(ref), "sistema", json.dumps({"origen": "referencia_tesis"})))
            fila = {"id": cur.lastrowid, "json": json.dumps(ref)}
        cal = mcal.ajustar_catalogo(json.loads(fila["json"]), config()["carreras"])
        _cache["calib"], _cache["calib_id"] = cal, fila["id"]
        return cal, fila["id"]


# ───────────────────────── estudiantes ─────────────────────────
def _crear_estudiante(c, id_colegio: str, grado_actual=None):
    h = seguridad.hmac_id(id_colegio)
    fila = c.execute("SELECT id FROM estudiantes WHERE id_colegio_hmac=?", (h,)).fetchone()
    if fila:
        return fila["id"], False
    while True:
        nid = seguridad.nuevo_id_estudiante()
        if not c.execute("SELECT 1 FROM estudiantes WHERE id=?", (nid,)).fetchone():
            break
    nombre, genero = nombre_ficticio(nid)
    c.execute("INSERT INTO estudiantes(id, id_colegio_hmac, nombre, genero, nombre_ficticio, grado_actual, creado, actualizado)"
              " VALUES (?,?,?,?,1,?,?,?)", (nid, h, nombre, genero, grado_actual, bd.ahora(), bd.ahora()))
    return nid, True


def buscar_por_id_colegio(id_colegio: str):
    return bd.uno("SELECT id FROM estudiantes WHERE id_colegio_hmac=?", seguridad.hmac_id(id_colegio))


def _registros(est_id: str):
    return [{"id_colegio": est_id, "grado_actual": None, "grado": r["grado"], "anio": r["anio"], "materia": r["materia"],
             "nota": r["nota"], "letra": r["letra"]}
            for r in bd.todos("SELECT grado, anio, materia, nota, letra FROM calificaciones WHERE estudiante_id=? ORDER BY grado, anio, materia", est_id)]


def preparar_estudiante(est_id: str):
    prep = mnotas.preparar(_registros(est_id), config()["reglas"])
    e = bd.uno("SELECT grado_actual FROM estudiantes WHERE id=?", est_id)
    prep["grado_actual"] = (e or {}).get("grado_actual") or prep["grado_actual"]
    return prep


def aplicacion_vigente(est_id: str):
    r = bd.uno("SELECT id, fecha, modalidad, respuestas, origen FROM chaside WHERE estudiante_id=? AND anulado=0 "
               "ORDER BY fecha DESC, id DESC LIMIT 1", est_id)
    if not r:
        return None
    return {"id": r["id"], "fecha": r["fecha"], "modalidad": r["modalidad"], "origen": r["origen"],
            "respuestas": {int(k): v for k, v in json.loads(r["respuestas"]).items()}}


# ───────────────────────── importaciones ─────────────────────────
def _registrar_carga(c, tipo, nombre, contenido, usuario, resumen):
    cur = c.execute("INSERT INTO cargas(tipo, archivo, sha256, usuario, fecha, resumen) VALUES (?,?,?,?,?,?)",
                    (tipo, nombre, hashlib.sha256(contenido).hexdigest(), usuario, bd.ahora(), json.dumps(resumen, ensure_ascii=False)))
    return cur.lastrowid


def importar_notas(contenido: bytes, nombre: str, usuario: str):
    try:
        regs = mnotas.leer_reporte(contenido, nombre)
    except ValueError as e:
        raise ErrorUsuario(str(e))
    reglas = config()["reglas"]
    por_est = {}
    for r in regs:
        por_est.setdefault(r["id_colegio"], []).append(r)
    nuevos = actualizados = filas = descartadas = 0
    sin_regla, afectados = set(), []
    with bd.transaccion() as c:
        carga_id = _registrar_carga(c, "notas", nombre, contenido, usuario, {})
        for idc, rr in por_est.items():
            ga = max((int(r["grado_actual"]) for r in rr if r["grado_actual"] is not None), default=None)
            eid, es_nuevo = _crear_estudiante(c, idc, ga)
            nuevos += es_nuevo; actualizados += not es_nuevo
            if ga is not None:
                c.execute("UPDATE estudiantes SET grado_actual=?, actualizado=? WHERE id=?", (ga, bd.ahora(), eid))
            for r in rr:
                if r["grado"] not in mnotas.GRADOS_SECUNDARIA:       # minimización: solo se guarda secundaria
                    descartadas += 1
                    continue
                if cfg.clasificar(r["materia"], reglas)[1] == "sin_regla":
                    sin_regla.add(r["materia"].strip())
                c.execute("INSERT INTO calificaciones(estudiante_id, anio, grado, materia, nota, letra, carga_id) VALUES (?,?,?,?,?,?,?) "
                          "ON CONFLICT(estudiante_id, anio, grado, materia) DO UPDATE SET nota=excluded.nota, letra=excluded.letra, "
                          "carga_id=excluded.carga_id", (eid, r["anio"], r["grado"], r["materia"], r["nota"], r["letra"], carga_id))
                filas += 1
            afectados.append(eid)
        resumen = {"estudiantes": len(por_est), "nuevos": nuevos, "actualizados": actualizados, "filas_guardadas": filas,
                   "filas_otros_niveles": descartadas, "materias_sin_regla": sorted(sin_regla)}
        c.execute("UPDATE cargas SET resumen=? WHERE id=?", (json.dumps(resumen, ensure_ascii=False), carga_id))
    bd.auditar(usuario, None, "cargar_notas", nombre, resumen)
    resumen["trabajo"] = lanzar_trabajo("recalcular", usuario, lambda t: recalcular(afectados, t))
    return resumen


def importar_nomina(contenido: bytes, nombre: str, usuario: str):
    """CSV: id_colegio, nombre, genero (F/M), grado_actual, paralelo. Reemplaza los nombres ficticios por los reales."""
    texto = contenido.decode("utf-8-sig", errors="replace")
    filas = list(csv.DictReader(io.StringIO(texto)))
    if not filas or "id_colegio" not in filas[0] or "nombre" not in filas[0]:
        raise ErrorUsuario("La nómina debe tener al menos las columnas id_colegio y nombre.")
    n = nuevos = 0
    with bd.transaccion() as c:
        _registrar_carga(c, "nomina", nombre, contenido, usuario, {"filas": len(filas)})
        for r in filas:
            idc = (r.get("id_colegio") or "").strip()
            nom = " ".join((r.get("nombre") or "").split())
            if not idc or not nom:
                continue
            ga = r.get("grado_actual")
            eid, es_nuevo = _crear_estudiante(c, idc, int(ga) if ga and str(ga).isdigit() else None)
            g = (r.get("genero") or "").strip().upper()[:1] or None
            c.execute("UPDATE estudiantes SET nombre=?, genero=COALESCE(?, genero), nombre_ficticio=0, grado_actual=COALESCE(?, grado_actual), "
                      "paralelo=COALESCE(?, paralelo), actualizado=? WHERE id=?",
                      (nom, g if g in ("F", "M") else None, int(ga) if ga and str(ga).isdigit() else None,
                       (r.get("paralelo") or "").strip() or None, bd.ahora(), eid))
            n += 1; nuevos += es_nuevo
    invalidar_cohorte()
    bd.auditar(usuario, None, "cargar_nomina", nombre, {"actualizados": n, "nuevos": nuevos})
    return {"actualizados": n, "nuevos": nuevos}


def _validar_respuestas(resp: dict, claves) -> dict:
    items = {i for i, _, _ in claves}
    out = {}
    for k, v in (resp or {}).items():
        try:
            i = int(str(k).lstrip("Pp"))
        except ValueError:
            continue
        if i in items:
            out[i] = mch.normalizar_respuesta(v)
    if sum(1 for v in out.values() if v in (0, 1)) == 0:
        raise ErrorUsuario("No hay respuestas válidas.")
    return {i: out.get(i) for i in sorted(items)}


def registrar_chaside(est_id: str, respuestas: dict, fecha: str | None, modalidad: str, origen: str, usuario: str | None,
                      recalcular_ya: bool = True):
    claves = config()["claves"]
    resp = _validar_respuestas(respuestas, claves)
    try:
        f = datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date() if fecha else date.today()
    except ValueError:
        raise ErrorUsuario("Fecha de aplicación no válida (use AAAA-MM-DD).")
    if f > date.today():
        raise ErrorUsuario("La fecha de aplicación no puede estar en el futuro.")
    modalidad = "autonoma" if str(modalidad).lower().startswith("aut") else "supervisada"
    with bd.transaccion() as c:
        if not c.execute("SELECT 1 FROM estudiantes WHERE id=?", (est_id,)).fetchone():
            raise ErrorUsuario("Estudiante no encontrado.")
        cur = c.execute("INSERT INTO chaside(estudiante_id, fecha, modalidad, respuestas, origen, registrado_por, creado) VALUES (?,?,?,?,?,?,?)",
                        (est_id, f.isoformat(), modalidad, json.dumps(resp), origen, usuario, bd.ahora()))
    if recalcular_ya:
        recalcular([est_id])
    return cur.lastrowid


def anular_ultimo_chaside(est_id: str, usuario: str):
    ap = aplicacion_vigente(est_id)
    if not ap:
        raise ErrorUsuario("El estudiante no tiene un CHASIDE registrado.")
    with bd.transaccion() as c:
        c.execute("UPDATE chaside SET anulado=1 WHERE id=?", (ap["id"],))
    bd.auditar(usuario, None, "anular_chaside", est_id, {"chaside_id": ap["id"]})
    recalcular([est_id])


def importar_chaside(contenido: bytes, nombre: str, usuario: str):
    """CSV con columnas id (ID del colegio o seudónimo E-xxxxxx), fecha_aplicacion, modalidad, P1…P98."""
    texto = contenido.decode("utf-8-sig", errors="replace")
    filas = list(csv.DictReader(io.StringIO(texto)))
    if not filas:
        raise ErrorUsuario("El archivo está vacío.")
    col_id = next((k for k in filas[0] if k and k.strip().lower() in ("id", "id_colegio", "student id (system)")), list(filas[0])[0])
    ok, sin_est, errores, afectados = 0, [], [], []
    with bd.transaccion() as c:
        _registrar_carga(c, "chaside", nombre, contenido, usuario, {"filas": len(filas)})
        for n, r in enumerate(filas, 2):
            ident = (r.get(col_id) or "").strip()
            est = bd.uno("SELECT id FROM estudiantes WHERE id=?", ident) if ident.startswith("E-") else buscar_por_id_colegio(ident)
            if not est:
                eid, _ = _crear_estudiante(c, ident)                     # CHASIDE antes que notas: se crea el estudiante
            else:
                eid = est["id"]
            try:
                registrar_chaside(eid, {k: v for k, v in r.items() if k and k.strip().upper().startswith("P")},
                                  r.get("fecha_aplicacion"), r.get("modalidad") or "supervisada", "archivo", usuario, recalcular_ya=False)
                ok += 1; afectados.append(eid)
            except ErrorUsuario as e:
                errores.append(f"Fila {n}: {e}")
    bd.auditar(usuario, None, "cargar_chaside", nombre, {"registradas": ok, "errores": len(errores)})
    return {"registradas": ok, "errores": errores[:50], "trabajo": lanzar_trabajo("recalcular", usuario, lambda t: recalcular(afectados, t))}


# ───────────────────────── códigos para que el estudiante responda en línea ─────────────────────────
def generar_codigos(est_ids: list[str], modalidad: str, usuario: str, dias: int | None = None):
    dias = dias or ajustes.DIAS_CODIGO
    modalidad = "autonoma" if str(modalidad).lower().startswith("aut") else "supervisada"
    out = []
    with bd.transaccion() as c:
        for eid in est_ids:
            e = c.execute("SELECT id, nombre FROM estudiantes WHERE id=? AND activo=1", (eid,)).fetchone()
            if not e:
                continue
            c.execute("DELETE FROM codigos WHERE estudiante_id=? AND usado IS NULL", (eid,))     # uno vigente por estudiante
            cod = seguridad.nuevo_codigo()
            c.execute("INSERT INTO codigos(estudiante_id, hash, modalidad, creado_por, creado, expira) VALUES (?,?,?,?,?,?)",
                      (eid, seguridad.hash_codigo(cod), modalidad, usuario, bd.ahora(),
                       (datetime.now() + timedelta(days=dias)).isoformat(timespec="seconds")))
            out.append({"id": eid, "nombre": e["nombre"], "codigo": cod})
    bd.auditar(usuario, None, "generar_codigos", None, {"n": len(out), "modalidad": modalidad, "dias": dias})
    return {"codigos": out, "expira_dias": dias, "modalidad": modalidad}


def _codigo_valido(codigo: str):
    if not seguridad.normalizar_codigo(codigo):
        return None
    r = bd.uno("SELECT c.id, c.estudiante_id, c.modalidad, c.expira, c.usado, e.nombre FROM codigos c "
               "JOIN estudiantes e ON e.id=c.estudiante_id WHERE c.hash=? AND e.activo=1", seguridad.hash_codigo(codigo))
    if not r or r["usado"] or r["expira"] < datetime.now().isoformat(timespec="seconds"):
        return None
    return r


def abrir_con_codigo(codigo: str):
    r = _codigo_valido(codigo)
    if not r:
        raise ErrorUsuario("El código no es válido, ya se usó o venció. Pide uno nuevo a tu orientador(a).")
    cf = config()
    return {"nombre": r["nombre"].split()[0], "modalidad": r["modalidad"],
            "preguntas": [{"item": i, "texto": cf["preguntas"].get(i, f"Pregunta {i}")} for i, _, _ in cf["claves"]],
            "preguntas_origen": cf["preguntas_origen"]}


def enviar_con_codigo(codigo: str, respuestas: dict):
    r = _codigo_valido(codigo)
    if not r:
        raise ErrorUsuario("El código no es válido, ya se usó o venció. Pide uno nuevo a tu orientador(a).")
    with bd.transaccion() as c:          # se marca como usado antes de guardar: un código, una respuesta
        n = c.execute("UPDATE codigos SET usado=? WHERE id=? AND usado IS NULL", (bd.ahora(), r["id"])).rowcount
        if n != 1:
            raise ErrorUsuario("Este código ya se usó.")
        registrar_chaside(r["estudiante_id"], respuestas, date.today().isoformat(), r["modalidad"], "en_linea", None, recalcular_ya=False)
    recalcular([r["estudiante_id"]])
    return {"ok": True}


# ───────────────────────── cálculo de resultados ─────────────────────────
def invalidar_cohorte():
    with _lock_cache:
        _cache["cohorte"] = None
        _cache["version"] += 1


def recalcular(est_ids: list[str] | None, trabajo_id: int | None = None):
    """Calcula (o borra) el resultado de los estudiantes indicados; None = todos."""
    cf = config()
    cal, cal_id = calibracion_activa()
    if est_ids is None:
        est_ids = [r["id"] for r in bd.todos("SELECT id FROM estudiantes WHERE activo=1")]
    est_ids = list(dict.fromkeys(est_ids))
    hoy = date.today()
    generado = datetime.now().isoformat(timespec="seconds")
    hechos = sin_nucleo = 0
    for k, eid in enumerate(est_ids, 1):
        e = bd.uno("SELECT id, nombre, genero, nombre_ficticio FROM estudiantes WHERE id=?", eid)
        if not e:
            continue
        prep = preparar_estudiante(eid)
        ap = aplicacion_vigente(eid)
        if prep["por_materia"] and ap:
            r = mres.evaluar_estudiante({"id": eid, "nombre": e["nombre"], "genero": e["genero"],
                                         "nombre_ficticio": bool(e["nombre_ficticio"])}, prep, ap, cal, cf["claves"],
                                        cf["carreras"], hoy, cf["fuentes"], generado)
            with bd.transaccion() as c:
                c.execute("INSERT INTO resultados(estudiante_id, json, indice, calibracion_id, generado) VALUES (?,?,?,?,?) "
                          "ON CONFLICT(estudiante_id) DO UPDATE SET json=excluded.json, indice=excluded.indice, "
                          "calibracion_id=excluded.calibracion_id, generado=excluded.generado",
                          (eid, json.dumps(r, ensure_ascii=False), json.dumps(mres.entrada_indice(r), ensure_ascii=False), cal_id, generado))
            hechos += 1
        else:
            with bd.transaccion() as c:
                c.execute("DELETE FROM resultados WHERE estudiante_id=?", (eid,))
            sin_nucleo += 1
        if trabajo_id and (k % 10 == 0 or k == len(est_ids)):
            _avance(trabajo_id, k / len(est_ids), f"{k} de {len(est_ids)} estudiantes")
    invalidar_cohorte()
    return {"calculados": hechos, "sin_nucleo_completo": sin_nucleo}


def _nombres():
    return {r["id"]: r for r in bd.todos("SELECT id, nombre, genero, nombre_ficticio FROM estudiantes")}


def resultado_estudiante(est_id: str):
    r = bd.uno("SELECT json FROM resultados WHERE estudiante_id=?", est_id)
    if not r:
        return None
    d = json.loads(r["json"])
    e = bd.uno("SELECT nombre, genero, nombre_ficticio, grado_actual FROM estudiantes WHERE id=?", est_id)
    if e:
        d["estudiante"].update(nombre=e["nombre"], genero=e["genero"], nombre_ficticio=bool(e["nombre_ficticio"]))
    return d


def cohorte():
    with _lock_cache:
        if _cache["cohorte"] is not None:
            return _cache["cohorte"]
    cf = config()
    cal, _ = calibracion_activa()
    nom = _nombres()
    indice = []
    for r in bd.todos("SELECT estudiante_id, indice FROM resultados r JOIN estudiantes e ON e.id=r.estudiante_id WHERE e.activo=1"):
        x = json.loads(r["indice"])
        e = nom.get(r["estudiante_id"])
        if e:
            x.update(nombre=e["nombre"], genero=e["genero"], nombre_ficticio=bool(e["nombre_ficticio"]))
        indice.append(x)
    c = mres.cohorte_json(indice, cal, cf["claves"], cf["preguntas"], cf["preguntas_origen"])
    c["evaluacion"] = cal.get("evaluacion")
    with _lock_cache:
        _cache["cohorte"] = c
    return c


def carreras():
    cal, _ = calibracion_activa()
    return mres.carreras_json(cal, config()["carreras"])


def lista_estudiantes():
    filas = bd.todos("""
      SELECT e.id, e.nombre, e.genero, e.nombre_ficticio, e.grado_actual, e.paralelo, e.activo,
        (SELECT COUNT(*) FROM calificaciones q WHERE q.estudiante_id=e.id) AS n_notas,
        (SELECT MAX(fecha) FROM chaside h WHERE h.estudiante_id=e.id AND h.anulado=0) AS chaside_fecha,
        (SELECT origen FROM chaside h WHERE h.estudiante_id=e.id AND h.anulado=0 ORDER BY fecha DESC, id DESC LIMIT 1) AS chaside_origen,
        (SELECT generado FROM resultados r WHERE r.estudiante_id=e.id) AS resultado,
        (SELECT expira FROM codigos c WHERE c.estudiante_id=e.id AND c.usado IS NULL AND c.expira > ?) AS codigo_expira
      FROM estudiantes e ORDER BY e.nombre""", datetime.now().isoformat(timespec="seconds"))
    for f in filas:
        f["nombre_ficticio"] = bool(f["nombre_ficticio"])
        f["estado"] = ("listo" if f["resultado"] else "falta_chaside" if f["n_notas"] else
                       "falta_notas" if f["chaside_fecha"] else "sin_datos")
    return filas


def materias_sin_regla():
    reglas = config()["reglas"]
    cuenta = {}
    for r in bd.todos("SELECT materia, COUNT(DISTINCT estudiante_id) n FROM calificaciones GROUP BY materia"):
        if cfg.clasificar(r["materia"], reglas)[1] == "sin_regla":
            cuenta[r["materia"].strip()] = cuenta.get(r["materia"].strip(), 0) + r["n"]
    return [{"materia": k, "estudiantes": v} for k, v in sorted(cuenta.items(), key=lambda t: -t[1])]


def clasificacion_materias():
    reglas = config()["reglas"]
    out = []
    for r in bd.todos("SELECT materia, COUNT(DISTINCT estudiante_id) n FROM calificaciones GROUP BY materia ORDER BY materia"):
        regla, estado = cfg.clasificar(r["materia"], reglas)
        out.append({"materia": r["materia"].strip(), "estudiantes": r["n"], "estado": estado,
                    "regla": regla.indice if regla else None, "areas": regla.areas if regla and estado == "incluida" else ""})
    return out


# ───────────────────────── recalibración ─────────────────────────
def recalibrar(usuario: str, trabajo_id: int | None = None):
    cf = config()
    previa, _ = calibracion_activa()
    cohorte_datos = []
    ids = [r["id"] for r in bd.todos("SELECT id FROM estudiantes WHERE activo=1")]
    for k, eid in enumerate(ids, 1):
        cohorte_datos.append({"id": eid, "prep": preparar_estudiante(eid), "chaside": aplicacion_vigente(eid)})
        if trabajo_id and k % 25 == 0:
            _avance(trabajo_id, 0.3 * k / len(ids), "Leyendo datos de la cohorte…")
    if trabajo_id:
        _avance(trabajo_id, 0.35, "Calibrando el modelo…")
    nueva = mcal.calibrar(cohorte_datos, cf["claves"], cf["carreras"], previa, date.today(), cf["fuentes"])
    nueva["evaluacion"] = previa.get("evaluacion")
    if not nueva["detalle"]["recalibrado"]:
        raise ErrorUsuario("Aún no hay datos suficientes para recalibrar: se necesitan al menos "
                           f"{mcal.MIN_NOTAS} estudiantes con notas o {mcal.MIN_CHASIDE} con CHASIDE. Se mantiene la calibración actual.")
    with bd.transaccion() as c:
        c.execute("UPDATE calibraciones SET activa=0")
        c.execute("INSERT INTO calibraciones(fecha, json, activa, usuario, resumen) VALUES (?,?,1,?,?)",
                  (bd.ahora(), json.dumps(nueva), usuario, json.dumps(nueva["detalle"], ensure_ascii=False)))
    with _lock_cache:
        _cache["calib"] = None
    bd.auditar(usuario, None, "recalibrar", None, nueva["detalle"])
    if trabajo_id:
        _avance(trabajo_id, 0.5, "Recalculando a todos los estudiantes…")
    recalcular(None, None)
    return nueva["detalle"]


def activar_calibracion(cal_id: int, usuario: str):
    if not bd.uno("SELECT id FROM calibraciones WHERE id=?", cal_id):
        raise ErrorUsuario("Calibración no encontrada.")
    with bd.transaccion() as c:
        c.execute("UPDATE calibraciones SET activa = (id = ?)", (cal_id,))
    with _lock_cache:
        _cache["calib"] = None
    bd.auditar(usuario, None, "activar_calibracion", str(cal_id))
    return lanzar_trabajo("recalcular", usuario, lambda t: recalcular(None, t))


# ───────────────────────── trabajos en segundo plano ─────────────────────────
def _avance(tid, p, msg):
    with bd.transaccion() as c:
        c.execute("UPDATE trabajos SET progreso=?, mensaje=? WHERE id=?", (round(p, 3), msg, tid))


def lanzar_trabajo(tipo: str, usuario: str, funcion) -> int:
    with bd.transaccion() as c:
        tid = c.execute("INSERT INTO trabajos(tipo, estado, usuario, creado, mensaje) VALUES (?,?,?,?,?)",
                        (tipo, "en_cola", usuario, bd.ahora(), "En cola…")).lastrowid

    def correr():
        with _lock_trabajo:                       # uno a la vez
            with bd.transaccion() as c:
                c.execute("UPDATE trabajos SET estado='en_curso' WHERE id=?", (tid,))
            try:
                res = funcion(tid)
                estado, msg = "listo", json.dumps(res, ensure_ascii=False) if res is not None else "Listo"
            except ErrorUsuario as e:
                estado, msg = "error", str(e)
            except Exception:                    # noqa: BLE001
                traceback.print_exc()
                estado, msg = "error", "Error interno: revise los registros del servidor."
            with bd.transaccion() as c:
                c.execute("UPDATE trabajos SET estado=?, progreso=1, mensaje=?, terminado=? WHERE id=?", (estado, msg, bd.ahora(), tid))

    threading.Thread(target=correr, daemon=True, name=f"trabajo-{tid}").start()
    return tid


def trabajo(tid: int):
    return bd.uno("SELECT id, tipo, estado, progreso, mensaje, creado, terminado FROM trabajos WHERE id=?", tid)
