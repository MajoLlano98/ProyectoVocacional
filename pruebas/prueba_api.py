"""
Prueba de punta a punta del servidor en marcha.
Uso: python pruebas/prueba_api.py http://localhost:8800 admin@colegio.ec ClaveSegura123 orienta@colegio.ec ClaveSegura123
"""
import os
import sys
import time

import requests

BASE, ADMIN, CLAVE_A, ORI, CLAVE_O = sys.argv[1:6]
H = {"X-Vocacional": "1"}
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fallos = []


def ok(cond, msg):
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        fallos.append(msg)


def sesion(u, c):
    s = requests.Session()
    r = s.post(f"{BASE}/api/sesion", json={"usuario": u, "clave": c}, headers=H)
    ok(r.status_code == 200, f"login {u}")
    return s


def esperar(s, tid):
    for _ in range(300):
        t = s.get(f"{BASE}/api/trabajos/{tid}").json()
        if t["estado"] in ("listo", "error"):
            return t
        time.sleep(0.2)
    return t


print("Seguridad")
ok(requests.get(f"{BASE}/datos/cohorte.json").status_code == 401, "datos sin sesión → 401")
ok(requests.post(f"{BASE}/api/sesion", json={"usuario": ADMIN, "clave": "mal"}).status_code == 403, "POST sin cabecera CSRF → 403")
ok(requests.post(f"{BASE}/api/sesion", json={"usuario": ADMIN, "clave": "mal"}, headers=H).status_code == 401, "contraseña incorrecta → 401")
r = requests.get(f"{BASE}/api/salud")
ok("Content-Security-Policy" in r.headers and r.headers.get("X-Frame-Options") == "DENY", "cabeceras de seguridad")

a = sesion(ADMIN, CLAVE_A)
o = sesion(ORI, CLAVE_O)
ok(o.post(f"{BASE}/api/cargas/notas", headers=H, files={"archivo": ("x.csv", b"a,b\n1,2\n")}).status_code == 403, "orientador no puede cargar notas")

print("Carga de notas")
with open(os.path.join(RAIZ, "pruebas", "datos", "reporte_ejemplo.csv"), "rb") as f:
    r = a.post(f"{BASE}/api/cargas/notas", headers=H, files={"archivo": ("reporte_ejemplo.csv", f.read(), "text/csv")})
d = r.json()
ok(r.status_code == 200 and d["estudiantes"] == 40, f"40 estudiantes importados ({d.get('filas_guardadas')} filas de secundaria, {d.get('filas_otros_niveles')} de otros niveles descartadas)")
ok(esperar(a, d["trabajo"])["estado"] == "listo", "recalcular tras la carga")
r = a.post(f"{BASE}/api/cargas/notas", headers=H, files={"archivo": ("malo.csv", b"col1,col2\n1,2\n")})
ok(r.status_code == 400 and "faltan columnas" in r.json()["error"], "archivo sin columnas → mensaje claro")
lista = o.get(f"{BASE}/api/estudiantes").json()
ok(len(lista) == 40 and all(e["estado"] == "falta_chaside" for e in lista), "estado: falta CHASIDE")
ok(all(e["nombre_ficticio"] for e in lista), "nombres ficticios asignados")
ok(not any("8100000" in str(e) for e in lista), "el ID del colegio no aparece en la API")

print("Códigos y CHASIDE en línea")
r = o.post(f"{BASE}/api/codigos", headers=H, json={"ids": [lista[0]["id"], lista[1]["id"]], "modalidad": "autonoma"})
cods = r.json()["codigos"]
ok(len(cods) == 2 and len(cods[0]["codigo"]) == 9, f"2 códigos generados (ej. {cods[0]['codigo']})")
pub = requests.Session()
r = pub.post(f"{BASE}/api/chaside/abrir", headers=H, json={"codigo": cods[0]["codigo"].lower().replace("-", " ")})
ok(r.status_code == 200 and len(r.json()["preguntas"]) == 98, "abrir test con código (minúsculas y espacios se aceptan)")
ok(pub.post(f"{BASE}/api/chaside/abrir", headers=H, json={"codigo": "AAAA-BBBB"}).status_code == 400, "código inválido → 400")
import random
rnd = random.Random(1)
resp = {str(i): rnd.choice([1, 0]) for i in range(1, 99)}
r = pub.post(f"{BASE}/api/chaside/enviar", headers=H, json={"codigo": cods[0]["codigo"], "respuestas": resp})
ok(r.status_code == 200, "enviar respuestas")
ok(pub.post(f"{BASE}/api/chaside/enviar", headers=H, json={"codigo": cods[0]["codigo"], "respuestas": resp}).status_code == 400, "el código no se puede reutilizar")

print("CHASIDE registrado por el DECE")
r = o.post(f"{BASE}/api/estudiantes/{lista[2]['id']}/chaside", headers=H,
           json={"respuestas": {str(i): rnd.choice([1, 0, None]) for i in range(1, 99)}, "fecha": "2026-09-15", "modalidad": "supervisada"})
ok(r.status_code == 200 and r.json()["resultado"] is not None, "registro supervisado → resultado inmediato")

print("Datos para la interfaz")
c = o.get(f"{BASE}/datos/cohorte.json").json()
ok(c["n_estudiantes"] == 2, f"cohorte con {c['n_estudiantes']} estudiantes con núcleo completo")
k = o.get(f"{BASE}/datos/carreras.json").json()
ok(len(k["carreras"]) == 87 and k["gamma"] == 3.0, "catálogo de carreras (87, γ=3)")
eid = c["estudiantes"][0]["id"]
e = o.get(f"{BASE}/datos/estudiantes/{eid}.json").json()
ok(len(e["areas"]) == 7 and len(e["carreras"]) == 10 and e["origen"]["chaside"]["total"] == 98, "JSON del estudiante completo")
ok(o.get(f"{BASE}/datos/estudiantes/{lista[1]['id']}.json").status_code == 404, "estudiante sin CHASIDE → 404 con explicación")

print("Modelo, materias y administración")
m = o.get(f"{BASE}/api/modelo").json()
ok(m["origen"] == "referencia_tesis" and m["conteos"]["listos"] == 2, "calibración de referencia activa")
t = esperar(a, a.post(f"{BASE}/api/modelo/recalibrar", headers=H).json()["trabajo"])
import json
det = json.loads(t["mensaje"]) if t["estado"] == "listo" else {}
ok(list(det.get("recalibrado", {})) == ["notas"] and "aprender" in det.get("conservado_de_previa", []),
   "recalibrar con 40 estudiantes → solo normas de notas; el resto se conserva (faltan datos)")
mat = o.get(f"{BASE}/api/materias").json()
ok(any(x["estado"] == "excluida" for x in mat) and all(x["estado"] != "sin_regla" for x in mat), f"{len(mat)} materias clasificadas, ninguna sin regla")
r = a.put(f"{BASE}/api/config/mapeo", headers=H, json={"reglas": [{"patron": "([", "incluir": "si", "pesos": {"C": 1}}]})
ok(r.status_code == 400, "regla con regex inválida → rechazada")
ok(a.post(f"{BASE}/api/usuarios", headers=H, json={"usuario": "x@y.ec", "nombre": "X", "rol": "orientador", "clave": "corta"}).status_code == 400, "contraseña débil rechazada")
r = a.get(f"{BASE}/api/exportar/resultados.csv")
ok(r.status_code == 200 and r.text.count("\n") == 3, "exportar CSV de resultados")
r = a.post(f"{BASE}/api/respaldos", headers=H)
ok(r.status_code == 200 and len(r.json()) >= 1, "respaldo manual")
au = a.get(f"{BASE}/api/auditoria").json()
acc = {x["accion"] for x in au}
ok({"login", "cargar_notas", "generar_codigos", "chaside_en_linea", "ver_estudiante", "login_fallido"} <= acc, "bitácora registra las acciones")
r = o.delete(f"{BASE}/api/estudiantes/{lista[2]['id']}/chaside", headers=H)
ok(r.status_code == 200 and o.get(f"{BASE}/datos/cohorte.json").json()["n_estudiantes"] == 1, "anular CHASIDE → sale de la cohorte")
r = o.delete(f"{BASE}/api/sesion", headers=H)
ok(o.get(f"{BASE}/datos/cohorte.json").status_code == 401, "cerrar sesión")
for _ in range(5):
    requests.post(f"{BASE}/api/sesion", json={"usuario": ORI, "clave": "mal"}, headers=H)
ok(requests.post(f"{BASE}/api/sesion", json={"usuario": ORI, "clave": CLAVE_O}, headers=H).status_code == 429, "bloqueo tras 5 intentos fallidos")

print(f"\n{'TODO BIEN' if not fallos else f'{len(fallos)} FALLO(S)'}")
sys.exit(1 if fallos else 0)
