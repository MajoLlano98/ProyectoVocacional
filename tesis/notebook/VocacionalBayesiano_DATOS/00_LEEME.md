# VocacionalBayesiano · Datos
- 01_entrada: aquí se publican los datos. nucleo/ es obligatorio (notas + chaside); complementarias/ es opcional.
- Formato CSV UTF-8. Nombre: fuente_institucion_AAAA-MM.csv. Nunca sobrescribir: cada entrega es un archivo nuevo.
- 02_configuracion: reglas editables (fichas de fuentes, mapeo de materias, claves CHASIDE).
- 03_referencias: carreras por país (reemplazable).
- 04_procesado y 05_salidas: los genera el notebook. No editar a mano.
- Privacidad: los nombres se seudonimizan; la tabla nombre<->ID vive solo en 04_procesado/privado/.