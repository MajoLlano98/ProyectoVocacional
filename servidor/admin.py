"""
Comandos de administración (se ejecutan en el servidor):

  python -m servidor.admin crear-usuario --usuario dece@colegio.edu.ec --nombre "Ana Pérez" --rol admin
  python -m servidor.admin clave --usuario dece@colegio.edu.ec
  python -m servidor.admin respaldo
  python -m servidor.admin recalcular
  python -m servidor.admin importar-notas RUTA.csv
  python -m servidor.admin demo            # datos de prueba ficticios + CHASIDE simulado

Con Docker:  docker compose exec app python -m servidor.admin <comando>
"""
import argparse
import getpass
import os
import random
import sys
from datetime import date

from . import ajustes, bd, respaldo, seguridad, servicio


def _iniciar():
    bd.iniciar()
    servicio.preparar_config()


def crear_usuario(a):
    clave = a.clave or getpass.getpass("Contraseña (mín. 10, con mayúsculas, minúsculas y números): ")
    msg = seguridad.validar_clave_nueva(clave)
    if msg:
        sys.exit(msg)
    with bd.transaccion() as c:
        c.execute("INSERT INTO usuarios(usuario, nombre, rol, hash, creado) VALUES (?,?,?,?,?)",
                  (a.usuario.strip().lower(), a.nombre, a.rol, seguridad.hash_clave(clave), bd.ahora()))
    bd.auditar("consola", "local", "crear_usuario", a.usuario, {"rol": a.rol})
    print(f"✓ Usuario {a.usuario} creado ({a.rol}).")


def cambiar_clave(a):
    clave = getpass.getpass("Nueva contraseña: ")
    msg = seguridad.validar_clave_nueva(clave)
    if msg:
        sys.exit(msg)
    with bd.transaccion() as c:
        n = c.execute("UPDATE usuarios SET hash=?, activo=1, version_sesion=version_sesion+1 WHERE usuario=?",
                      (seguridad.hash_clave(clave), a.usuario.strip().lower())).rowcount
    if not n:
        sys.exit("Usuario no encontrado.")
    bd.auditar("consola", "local", "cambiar_clave", a.usuario)
    print("✓ Contraseña actualizada.")


def demo(a):
    """Carga datos de prueba para conocer la aplicación (no usar con datos reales)."""
    ruta = a.reporte or os.path.join(ajustes.RAIZ, "pruebas", "datos", "reporte_ejemplo.csv")
    with open(ruta, "rb") as f:
        r = servicio.importar_notas(f.read(), os.path.basename(ruta), "demo")
    print("Notas:", {k: v for k, v in r.items() if k != "trabajo"})
    claves = servicio.config()["claves"]
    for e in servicio.lista_estudiantes():
        rnd = random.Random(e["id"])
        sesgo = {a: rnd.uniform(0.2, 0.8) for a in "CHASIDE"}
        resp = {i: int(rnd.random() < sesgo[ar]) for i, ar, _ in claves}
        servicio.registrar_chaside(e["id"], resp, date.today().isoformat(), "supervisada", "dece", "demo", recalcular_ya=False)
    print("Calculando…", servicio.recalcular(None))


def main():
    p = argparse.ArgumentParser(prog="python -m servidor.admin", description="Administración del Sistema Vocacional")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("crear-usuario"); x.add_argument("--usuario", required=True); x.add_argument("--nombre", required=True)
    x.add_argument("--rol", choices=["admin", "orientador"], default="orientador"); x.add_argument("--clave")
    x = s.add_parser("clave"); x.add_argument("--usuario", required=True)
    s.add_parser("respaldo"); s.add_parser("recalcular")
    x = s.add_parser("importar-notas"); x.add_argument("archivo")
    x = s.add_parser("demo"); x.add_argument("--reporte")
    a = p.parse_args()
    _iniciar()
    if a.cmd == "crear-usuario":
        crear_usuario(a)
    elif a.cmd == "clave":
        cambiar_clave(a)
    elif a.cmd == "respaldo":
        print("✓", respaldo.respaldar("manual"))
    elif a.cmd == "recalcular":
        print(servicio.recalcular(None))
    elif a.cmd == "importar-notas":
        with open(a.archivo, "rb") as f:
            r = servicio.importar_notas(f.read(), os.path.basename(a.archivo), "consola")
        print({k: v for k, v in r.items() if k != "trabajo"})
        servicio.recalcular(None)
    elif a.cmd == "demo":
        demo(a)


if __name__ == "__main__":
    main()
