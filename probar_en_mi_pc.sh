#!/usr/bin/env bash
# Prueba local en Mac o Linux (datos ficticios). Uso: bash probar_en_mi_pc.sh
set -euo pipefail
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && { echo "Instala Python 3.13 desde https://www.python.org/downloads/"; exit 1; }
[ -d .venv ] || { echo "Primera vez: preparando el entorno (1-3 minutos)…"; "$PY" -m venv .venv; }
source .venv/bin/activate
python -m pip install -q --disable-pip-version-check -r requirements.txt
export VOCACIONAL_DATOS="$PWD/datos_prueba" VOCACIONAL_COOKIE_SEGURA=false VOCACIONAL_COLEGIO="Colegio de prueba"
if [ ! -f "$VOCACIONAL_DATOS/vocacional.db" ]; then
  echo "Creando usuarios y 40 estudiantes ficticios…"
  python -m servidor.admin crear-usuario --usuario admin@prueba.ec --nombre "Administradora" --rol admin --clave Prueba12345
  python -m servidor.admin crear-usuario --usuario orienta@prueba.ec --nombre "Orientadora" --rol orientador --clave Prueba12345
  python -m servidor.admin demo
fi
cat <<TXT

  LISTO → abre http://localhost:8000
    Administración: admin@prueba.ec   / Prueba12345
    Orientación:    orienta@prueba.ec / Prueba12345
    Test estudiante: http://localhost:8000/chaside
  Para detener: Ctrl+C
TXT
( sleep 4; (command -v open >/dev/null && open http://localhost:8000) || (command -v xdg-open >/dev/null && xdg-open http://localhost:8000) || true ) &
python -m uvicorn servidor.app:app --port 8000
