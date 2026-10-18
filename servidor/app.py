"""
Aplicación web: API JSON + interfaz. Ejecutar con:  uvicorn servidor.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import re
from datetime import datetime

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import modelo

from . import ajustes, bd, respaldo, seguridad, servicio
from .servicio import ErrorUsuario

ROLES = {"orientador": 1, "admin": 2}
METODOS_ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}


# ───────────────────────── utilidades ─────────────────────────
def error(msg: str, codigo: int = 400):
    return JSONResponse({"error": msg}, status_code=codigo)


def usuario_actual(request: Request):
    uid, v = request.session.get("uid"), request.session.get("v")
    if not uid:
        return None
    u = bd.uno("SELECT id, usuario, nombre, rol, activo, version_sesion FROM usuarios WHERE id=?", uid)
    if not u or not u["activo"] or u["version_sesion"] != v:
        request.session.clear()
        return None
    return u


def requiere(rol: str):
    """Decorador: exige sesión con el rol indicado (admin incluye a orientador)."""
    def deco(fn):
        async def envoltura(request: Request):
            u = usuario_actual(request)
            if not u:
                return error("Inicia sesión para continuar.", 401)
            if ROLES[u["rol"]] < ROLES[rol]:
                return error("No tienes permiso para esta acción.", 403)
            request.state.usuario = u
            try:
                return await fn(request)
            except ErrorUsuario as e:
                return error(str(e))
        return envoltura
    return deco


async def cuerpo_json(request: Request, maximo=512_000):
    crudo = await request.body()
    if len(crudo) > maximo:
        raise ErrorUsuario("La solicitud es demasiado grande.")
    try:
        return json.loads(crudo or b"{}")
    except json.JSONDecodeError:
        raise ErrorUsuario("Formato no válido.")


async def archivo_subido(request: Request):
    form = await request.form(max_files=1, max_fields=5)
    f = form.get("archivo")
    if f is None or not getattr(f, "filename", None):
        raise ErrorUsuario("Adjunta un archivo.")
    contenido = await f.read()
    if len(contenido) > ajustes.MAX_ARCHIVO_MB * 1024 * 1024:
        raise ErrorUsuario(f"El archivo supera {ajustes.MAX_ARCHIVO_MB} MB.")
    if not re.search(r"\.(csv|xlsx|xlsm)$", f.filename, re.I):
        raise ErrorUsuario("Formato no admitido: sube un archivo .csv o .xlsx.")
    return contenido, os.path.basename(f.filename)


class Seguridad(BaseHTTPMiddleware):
    """Cabeceras de seguridad, protección CSRF por cabecera propia e IP para la bitácora."""

    async def dispatch(self, request: Request, call_next):
        bd.IP_ACTUAL.set(seguridad.ip_cliente(request))
        if request.method in METODOS_ESCRITURA and request.url.path.startswith("/api/"):
            # Un formulario de otro sitio no puede enviar esta cabecera sin permiso CORS (que no se concede).
            if request.headers.get("x-vocacional") != "1":
                return error("Solicitud rechazada.", 403)
        r = await call_next(request)
        for k, v in seguridad.CABECERAS.items():
            r.headers.setdefault(k, v)
        if request.url.path.startswith(("/api/", "/datos/")):
            r.headers["Cache-Control"] = "no-store"
        return r


# ───────────────────────── páginas ─────────────────────────
async def inicio(request: Request):
    if not usuario_actual(request):
        return RedirectResponse("/entrar", 302)
    return FileResponse(os.path.join(ajustes.WEB, "index.html"))


async def pagina_entrar(request: Request):
    return FileResponse(os.path.join(ajustes.WEB, "entrar.html"))


async def pagina_chaside(request: Request):
    return FileResponse(os.path.join(ajustes.WEB, "chaside.html"))


async def salud(request: Request):
    return JSONResponse({"ok": True, "version": modelo.__version__})


# ───────────────────────── sesión ─────────────────────────
async def iniciar_sesion(request: Request):
    try:
        d = await cuerpo_json(request, 4096)
    except ErrorUsuario as e:
        return error(str(e))
    usuario = str(d.get("usuario", "")).strip().lower()[:120]
    clave = str(d.get("clave", ""))[:256]
    llave = f"{usuario}|{seguridad.ip_cliente(request)}"
    if seguridad.LOGIN.bloqueado(llave):
        return error("Demasiados intentos. Espera 15 minutos e inténtalo de nuevo.", 429)
    u = bd.uno("SELECT * FROM usuarios WHERE usuario=?", usuario)
    ok = await run_in_threadpool(seguridad.verificar_clave, clave, u["hash"] if u else seguridad.HASH_FICTICIO)
    if not u or not ok or not u["activo"]:
        seguridad.LOGIN.fallo(llave)
        bd.auditar(usuario or "?", None, "login_fallido")
        return error("Usuario o contraseña incorrectos.", 401)
    seguridad.LOGIN.limpiar(llave)
    request.session.clear()
    request.session.update({"uid": u["id"], "v": u["version_sesion"]})
    with bd.transaccion() as c:
        c.execute("UPDATE usuarios SET ultimo_acceso=? WHERE id=?", (bd.ahora(), u["id"]))
    bd.auditar(u["usuario"], None, "login")
    return JSONResponse({"ok": True})


async def cerrar_sesion(request: Request):
    u = usuario_actual(request)
    if u:
        bd.auditar(u["usuario"], None, "logout")
    request.session.clear()
    return JSONResponse({"ok": True})


async def yo(request: Request):
    u = usuario_actual(request)
    if not u:
        return error("Sin sesión.", 401)
    return JSONResponse({"usuario": u["usuario"], "nombre": u["nombre"], "rol": u["rol"],
                         "colegio": bd.ajuste("nombre_colegio", ajustes.NOMBRE_COLEGIO)})


@requiere("orientador")
async def cambiar_mi_clave(request: Request):
    d = await cuerpo_json(request, 4096)
    u = request.state.usuario
    fila = bd.uno("SELECT hash FROM usuarios WHERE id=?", u["id"])
    if not seguridad.verificar_clave(str(d.get("actual", "")), fila["hash"]):
        return error("La contraseña actual no es correcta.")
    msg = seguridad.validar_clave_nueva(str(d.get("nueva", "")))
    if msg:
        return error(msg)
    with bd.transaccion() as c:
        c.execute("UPDATE usuarios SET hash=?, version_sesion=version_sesion+1 WHERE id=?",
                  (seguridad.hash_clave(d["nueva"]), u["id"]))
    request.session.clear()
    bd.auditar(u["usuario"], None, "cambiar_clave")
    return JSONResponse({"ok": True, "mensaje": "Contraseña cambiada. Vuelve a iniciar sesión."})


# ───────────────────────── datos para la interfaz (mismo contrato que la tesis) ─────────────────────────
@requiere("orientador")
async def datos_cohorte(request: Request):
    return JSONResponse(await run_in_threadpool(servicio.cohorte))


@requiere("orientador")
async def datos_carreras(request: Request):
    return JSONResponse(await run_in_threadpool(servicio.carreras))


@requiere("orientador")
async def datos_estudiante(request: Request):
    eid = request.path_params["id"]
    d = await run_in_threadpool(servicio.resultado_estudiante, eid)
    if not d:
        return error("Este estudiante aún no tiene resultado (faltan notas o CHASIDE).", 404)
    bd.auditar(request.state.usuario["usuario"], None, "ver_estudiante", eid)
    return JSONResponse(d)


# ───────────────────────── estudiantes, CHASIDE y códigos ─────────────────────────
@requiere("orientador")
async def estudiantes(request: Request):
    return JSONResponse(await run_in_threadpool(servicio.lista_estudiantes))


@requiere("admin")
async def editar_estudiante(request: Request):
    eid = request.path_params["id"]
    d = await cuerpo_json(request, 4096)
    campos, vals = [], []
    if "activo" in d:
        campos.append("activo=?"); vals.append(1 if d["activo"] else 0)
    if "grado_actual" in d:
        campos.append("grado_actual=?"); vals.append(int(d["grado_actual"]) if d["grado_actual"] else None)
    if "paralelo" in d:
        campos.append("paralelo=?"); vals.append(str(d["paralelo"] or "")[:20] or None)
    if not campos:
        return error("Nada que actualizar.")
    with bd.transaccion() as c:
        n = c.execute(f"UPDATE estudiantes SET {', '.join(campos)}, actualizado=? WHERE id=?", (*vals, bd.ahora(), eid)).rowcount
    if not n:
        return error("Estudiante no encontrado.", 404)
    servicio.invalidar_cohorte()
    bd.auditar(request.state.usuario["usuario"], None, "editar_estudiante", eid, d)
    return JSONResponse({"ok": True})


@requiere("orientador")
async def chaside_dece(request: Request):
    """El DECE registra una aplicación del CHASIDE (en papel o en el aula) desde la ficha del estudiante."""
    eid = request.path_params["id"]
    d = await cuerpo_json(request)
    u = request.state.usuario["usuario"]
    await run_in_threadpool(servicio.registrar_chaside, eid, d.get("respuestas") or {}, d.get("fecha"),
                            d.get("modalidad", "supervisada"), "dece", u)
    bd.auditar(u, None, "registrar_chaside", eid)
    return JSONResponse({"ok": True, "resultado": await run_in_threadpool(servicio.resultado_estudiante, eid)})


@requiere("orientador")
async def chaside_anular(request: Request):
    eid = request.path_params["id"]
    await run_in_threadpool(servicio.anular_ultimo_chaside, eid, request.state.usuario["usuario"])
    return JSONResponse({"ok": True})


@requiere("orientador")
async def codigos(request: Request):
    d = await cuerpo_json(request)
    ids = [str(x) for x in (d.get("ids") or [])][:2000]
    if not ids:
        return error("Elige al menos un estudiante.")
    dias = int(d.get("dias") or ajustes.DIAS_CODIGO)
    if not 1 <= dias <= 120:
        return error("La vigencia debe estar entre 1 y 120 días.")
    r = await run_in_threadpool(servicio.generar_codigos, ids, d.get("modalidad", "supervisada"), request.state.usuario["usuario"], dias)
    return JSONResponse(r)


# ───────────────────────── CHASIDE en línea (estudiantes, sin cuenta) ─────────────────────────
async def chaside_abrir(request: Request):
    ip = seguridad.ip_cliente(request)
    if seguridad.CODIGO.bloqueado(ip):
        return error("Demasiados intentos. Espera unos minutos.", 429)
    try:
        d = await cuerpo_json(request, 2048)
        return JSONResponse(await run_in_threadpool(servicio.abrir_con_codigo, str(d.get("codigo", ""))))
    except ErrorUsuario as e:
        seguridad.CODIGO.fallo(ip)
        return error(str(e))


async def chaside_enviar(request: Request):
    ip = seguridad.ip_cliente(request)
    if seguridad.CODIGO.bloqueado(ip):
        return error("Demasiados intentos. Espera unos minutos.", 429)
    try:
        d = await cuerpo_json(request, 16384)
        r = await run_in_threadpool(servicio.enviar_con_codigo, str(d.get("codigo", "")), d.get("respuestas") or {})
        bd.auditar("estudiante", None, "chaside_en_linea")
        return JSONResponse(r)
    except ErrorUsuario as e:
        seguridad.CODIGO.fallo(ip)
        return error(str(e))


# ───────────────────────── cargas de archivos (administración) ─────────────────────────
@requiere("admin")
async def cargar_notas(request: Request):
    contenido, nombre = await archivo_subido(request)
    return JSONResponse(await run_in_threadpool(servicio.importar_notas, contenido, nombre, request.state.usuario["usuario"]))


@requiere("admin")
async def cargar_nomina(request: Request):
    contenido, nombre = await archivo_subido(request)
    return JSONResponse(await run_in_threadpool(servicio.importar_nomina, contenido, nombre, request.state.usuario["usuario"]))


@requiere("admin")
async def cargar_chaside(request: Request):
    contenido, nombre = await archivo_subido(request)
    return JSONResponse(await run_in_threadpool(servicio.importar_chaside, contenido, nombre, request.state.usuario["usuario"]))


@requiere("admin")
async def lista_cargas(request: Request):
    filas = bd.todos("SELECT id, tipo, archivo, usuario, fecha, resumen FROM cargas ORDER BY id DESC LIMIT 100")
    for f in filas:
        f["resumen"] = json.loads(f["resumen"] or "{}")
    return JSONResponse(filas)


# ───────────────────────── materias y modelo ─────────────────────────
@requiere("orientador")
async def materias(request: Request):
    return JSONResponse(await run_in_threadpool(servicio.clasificacion_materias))


@requiere("admin")
async def mapeo(request: Request):
    if request.method == "GET":
        return JSONResponse([{"patron": r.patron, "incluir": r.incluir, "pesos": {a: int(r.pesos[a]) for a in modelo.CODIGOS},
                              "justificacion": r.justificacion} for r in servicio.config()["reglas"]])
    d = await cuerpo_json(request)
    tid = await run_in_threadpool(servicio.guardar_mapeo, d.get("reglas") or [], request.state.usuario["usuario"])
    return JSONResponse({"ok": True, "trabajo": tid})


@requiere("orientador")
async def estado_modelo(request: Request):
    cal, cal_id = servicio.calibracion_activa()
    hist = bd.todos("SELECT id, fecha, activa, usuario, resumen FROM calibraciones ORDER BY id DESC LIMIT 20")
    for h in hist:
        h["resumen"] = json.loads(h["resumen"] or "{}")
    lista = servicio.lista_estudiantes()
    cf = servicio.config()
    return JSONResponse({"activa": cal_id, "origen": cal.get("origen"), "fecha": cal.get("fecha"), "detalle": cal.get("detalle"),
                         "param": cal.get("param"), "gamma": cal["carreras"]["gamma"], "evaluacion": cal.get("evaluacion"),
                         "historial": hist, "minimos": {"notas": servicio.mcal.MIN_NOTAS, "chaside": servicio.mcal.MIN_CHASIDE,
                                                        "aprender": servicio.mcal.MIN_APRENDER},
                         "conteos": {"estudiantes": len(lista), "con_notas": sum(1 for e in lista if e["n_notas"]),
                                     "con_chaside": sum(1 for e in lista if e["chaside_fecha"]),
                                     "listos": sum(1 for e in lista if e["resultado"])},
                         "carreras": len(cf["carreras"]), "carreras_descartadas": cf["carreras_descartadas"],
                         "preguntas_origen": cf["preguntas_origen"], "version_modelo": modelo.__version__})


@requiere("admin")
async def recalibrar(request: Request):
    u = request.state.usuario["usuario"]
    tid = servicio.lanzar_trabajo("recalibrar", u, lambda t: servicio.recalibrar(u, t))
    return JSONResponse({"trabajo": tid})


@requiere("admin")
async def activar_calibracion(request: Request):
    tid = await run_in_threadpool(servicio.activar_calibracion, int(request.path_params["id"]), request.state.usuario["usuario"])
    return JSONResponse({"trabajo": tid})


@requiere("admin")
async def recalcular_todo(request: Request):
    tid = servicio.lanzar_trabajo("recalcular", request.state.usuario["usuario"], lambda t: servicio.recalcular(None, t))
    return JSONResponse({"trabajo": tid})


@requiere("orientador")
async def ver_trabajo(request: Request):
    t = servicio.trabajo(int(request.path_params["id"]))
    return JSONResponse(t) if t else error("No encontrado.", 404)


# ───────────────────────── usuarios, bitácora, ajustes, respaldos ─────────────────────────
@requiere("admin")
async def usuarios(request: Request):
    if request.method == "GET":
        return JSONResponse(bd.todos("SELECT id, usuario, nombre, rol, activo, creado, ultimo_acceso FROM usuarios ORDER BY nombre"))
    d = await cuerpo_json(request, 4096)
    usuario = str(d.get("usuario", "")).strip().lower()
    nombre = " ".join(str(d.get("nombre", "")).split())[:120]
    rol = d.get("rol", "orientador")
    if not re.fullmatch(r"[a-z0-9._@+-]{3,120}", usuario) or not nombre or rol not in ROLES:
        return error("Revisa usuario (correo o nombre de usuario), nombre y rol.")
    msg = seguridad.validar_clave_nueva(str(d.get("clave", "")))
    if msg:
        return error(msg)
    try:
        with bd.transaccion() as c:
            c.execute("INSERT INTO usuarios(usuario, nombre, rol, hash, creado) VALUES (?,?,?,?,?)",
                      (usuario, nombre, rol, seguridad.hash_clave(d["clave"]), bd.ahora()))
    except Exception:  # noqa: BLE001
        return error("Ese usuario ya existe.")
    bd.auditar(request.state.usuario["usuario"], None, "crear_usuario", usuario, {"rol": rol})
    return JSONResponse({"ok": True})


@requiere("admin")
async def editar_usuario(request: Request):
    uid = int(request.path_params["id"])
    d = await cuerpo_json(request, 4096)
    yo_ = request.state.usuario
    sets, vals = [], []
    if "activo" in d:
        if uid == yo_["id"] and not d["activo"]:
            return error("No puedes desactivar tu propia cuenta.")
        sets.append("activo=?"); vals.append(1 if d["activo"] else 0)
    if "rol" in d:
        if d["rol"] not in ROLES or (uid == yo_["id"] and d["rol"] != "admin"):
            return error("Rol no válido.")
        sets.append("rol=?"); vals.append(d["rol"])
    if d.get("clave"):
        msg = seguridad.validar_clave_nueva(str(d["clave"]))
        if msg:
            return error(msg)
        sets.append("hash=?"); vals.append(seguridad.hash_clave(d["clave"]))
    if not sets:
        return error("Nada que actualizar.")
    with bd.transaccion() as c:
        c.execute(f"UPDATE usuarios SET {', '.join(sets)}, version_sesion=version_sesion+1 WHERE id=?", (*vals, uid))
        quedan = c.execute("SELECT COUNT(*) FROM usuarios WHERE rol='admin' AND activo=1").fetchone()[0]
        if quedan == 0:
            raise ErrorUsuario("Debe quedar al menos un administrador activo.")
    bd.auditar(yo_["usuario"], None, "editar_usuario", str(uid), {k: ("***" if k == "clave" else v) for k, v in d.items()})
    return JSONResponse({"ok": True})


@requiere("admin")
async def auditoria(request: Request):
    lim = min(int(request.query_params.get("limite", 200)), 2000)
    return JSONResponse(bd.todos("SELECT fecha, usuario, ip, accion, objeto, detalle FROM auditoria ORDER BY id DESC LIMIT ?", lim))


@requiere("orientador")
async def ver_ajustes(request: Request):
    return JSONResponse({"nombre_colegio": bd.ajuste("nombre_colegio", ajustes.NOMBRE_COLEGIO),
                         "dias_codigo": ajustes.DIAS_CODIGO})


@requiere("admin")
async def guardar_ajustes(request: Request):
    d = await cuerpo_json(request, 4096)
    if "nombre_colegio" in d:
        bd.fijar_ajuste("nombre_colegio", " ".join(str(d["nombre_colegio"]).split())[:120])
    bd.auditar(request.state.usuario["usuario"], None, "ajustes", None, d)
    return JSONResponse({"ok": True})


@requiere("admin")
async def respaldos(request: Request):
    if request.method == "POST":
        ruta = await run_in_threadpool(respaldo.respaldar, "manual")
        bd.auditar(request.state.usuario["usuario"], None, "respaldo_manual", os.path.basename(ruta))
    return JSONResponse(respaldo.lista())


@requiere("admin")
async def exportar_resultados(request: Request):
    """Resumen por estudiante en CSV (para Excel). Se registra en la bitácora."""
    coh = await run_in_threadpool(servicio.cohorte)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "nombre", "nombre_ficticio", "grado"] + [f"{a}_{x}" for a in modelo.CODIGOS for x in ("interes_P", "rendimiento_P", "zona")]
               + ["carrera_1", "carrera_2", "carrera_3", "alertas"])
    for e in coh["estudiantes"]:
        w.writerow([e["id"], e["nombre"], e["nombre_ficticio"], e["grado_actual"]]
                   + [v for a in modelo.CODIGOS for v in e["perfil"][a]] + (e["top3"] + ["", "", ""])[:3] + [e["n_alertas"]])
    bd.auditar(request.state.usuario["usuario"], None, "exportar_resultados", None, {"n": len(coh["estudiantes"])})
    return Response("﻿" + out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="resultados_{datetime.now():%Y-%m-%d}.csv"'})


# ───────────────────────── manejo de errores ─────────────────────────
async def no_encontrado(request: Request, exc: HTTPException):
    if request.url.path.startswith(("/api/", "/datos/")):
        return error("No encontrado.", exc.status_code)
    return Response("No encontrado", status_code=exc.status_code, media_type="text/plain")


async def error_interno(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return error("Error interno del servidor.", 500)


@contextlib.asynccontextmanager
async def ciclo_de_vida(app):
    al_iniciar()
    yield


def al_iniciar():
    bd.iniciar()
    servicio.preparar_config()
    servicio.config()
    servicio.calibracion_activa()
    respaldo.programar(lambda: servicio.recalcular(None))   # cada noche: respaldo + recalcular antigüedad del CHASIDE


rutas = [
    Route("/", inicio), Route("/entrar", pagina_entrar), Route("/chaside", pagina_chaside), Route("/api/salud", salud),
    Route("/api/sesion", iniciar_sesion, methods=["POST"]), Route("/api/sesion", cerrar_sesion, methods=["DELETE"]),
    Route("/api/yo", yo), Route("/api/yo/clave", cambiar_mi_clave, methods=["POST"]),
    Route("/datos/cohorte.json", datos_cohorte), Route("/datos/carreras.json", datos_carreras),
    Route("/datos/estudiantes/{id}.json", datos_estudiante),
    Route("/api/estudiantes", estudiantes), Route("/api/estudiantes/{id}", editar_estudiante, methods=["PATCH"]),
    Route("/api/estudiantes/{id}/chaside", chaside_dece, methods=["POST"]),
    Route("/api/estudiantes/{id}/chaside", chaside_anular, methods=["DELETE"]),
    Route("/api/codigos", codigos, methods=["POST"]),
    Route("/api/chaside/abrir", chaside_abrir, methods=["POST"]), Route("/api/chaside/enviar", chaside_enviar, methods=["POST"]),
    Route("/api/cargas", lista_cargas), Route("/api/cargas/notas", cargar_notas, methods=["POST"]),
    Route("/api/cargas/nomina", cargar_nomina, methods=["POST"]), Route("/api/cargas/chaside", cargar_chaside, methods=["POST"]),
    Route("/api/materias", materias), Route("/api/config/mapeo", mapeo, methods=["GET", "PUT"]),
    Route("/api/modelo", estado_modelo), Route("/api/modelo/recalibrar", recalibrar, methods=["POST"]),
    Route("/api/modelo/recalcular", recalcular_todo, methods=["POST"]),
    Route("/api/modelo/activar/{id:int}", activar_calibracion, methods=["POST"]),
    Route("/api/trabajos/{id:int}", ver_trabajo),
    Route("/api/usuarios", usuarios, methods=["GET", "POST"]), Route("/api/usuarios/{id:int}", editar_usuario, methods=["PATCH"]),
    Route("/api/auditoria", auditoria), Route("/api/ajustes", ver_ajustes), Route("/api/ajustes", guardar_ajustes, methods=["PUT"]),
    Route("/api/respaldos", respaldos, methods=["GET", "POST"]), Route("/api/exportar/resultados.csv", exportar_resultados),
    Mount("/", StaticFiles(directory=ajustes.WEB), name="web"),
]

app = Starlette(
    routes=rutas,
    middleware=[
        Middleware(TrustedHostMiddleware, allowed_hosts=ajustes.HOSTS),
        Middleware(SessionMiddleware, secret_key=ajustes.secreto(), session_cookie="vocacional_sesion",
                   max_age=ajustes.HORAS_SESION * 3600, same_site="strict", https_only=ajustes.COOKIE_SEGURA),
        Middleware(Seguridad),
    ],
    exception_handlers={404: no_encontrado, 405: no_encontrado, 500: error_interno},
    lifespan=ciclo_de_vida,
)
