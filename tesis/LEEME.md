# Material de la tesis

Esta carpeta conserva **sin modificaciones** el trabajo académico. No la usa el servidor.

| Carpeta | Contenido |
|---|---|
| `notebook/VocacionalBayesiano.ipynb` | El Colab oficial (Módulos 0–9). Versión en Drive: ver el LEEME original |
| `notebook/VocacionalBayesiano_DATOS/` | Configuración y resultados procesados (seudónimos). Sin datos crudos de `01_entrada` ni la llave `04_procesado/privado` |
| `encuesta_validacion/sitio/` | Encuesta pública de validación retrospectiva con estudiantes universitarios (PHP). La clave de `config.php` se reemplazó por `cambia-esta-clave` |

El servidor reproduce los módulos 3, 4, 5, 7 y 9 en `../modelo/` y está validado contra las salidas de
`notebook/VocacionalBayesiano_DATOS/` con `../scripts/calibracion_referencia.py`.

Las respuestas descargadas de la encuesta **no** se incluyen en el repositorio (datos personales): guárdalas aparte.

**Etiquetas de versión sugeridas:** `v1.0-tesis` (lo que se defiende) y `v1.0-colegio` (lo que se entrega).
