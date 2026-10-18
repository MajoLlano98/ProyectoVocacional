#!/usr/bin/env bash
# Copia los respaldos fuera del servidor (un servidor puede perderse: disco dañado, cuenta cerrada…).
# Opción A · rclone a Google Drive / OneDrive del colegio (configurar antes con: rclone config)
# Opción B · rsync a otro equipo por SSH
# Programar a diario con cron (crontab -e):   30 3 * * *  /ruta/vocacional/despliegue/respaldo_externo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
DESTINO_RCLONE="${DESTINO_RCLONE:-drive_colegio:respaldos_vocacional}"
if command -v rclone >/dev/null; then
  rclone copy datos/respaldos "$DESTINO_RCLONE" --max-age 48h
  echo "✓ Respaldos copiados a $DESTINO_RCLONE"
else
  echo "Instala rclone (https://rclone.org/install/) o edita este script para usar rsync." >&2
  exit 1
fi
# ⚠ Guarda también una copia del archivo .env (contiene el secreto) en el gestor de contraseñas del colegio.
