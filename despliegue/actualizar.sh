#!/usr/bin/env bash
# Actualiza el sistema a la última versión del repositorio, con respaldo previo.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "→ Respaldo previo"
docker compose exec -T app python -m servidor.admin respaldo
echo "→ Descargando la nueva versión"
git pull --ff-only
echo "→ Reconstruyendo y reiniciando"
docker compose up -d --build
docker compose ps
echo "✓ Actualizado"
