# Manual técnico

## Arquitectura

| Capa | Tecnología | Por qué |
|---|---|---|
| Interfaz | HTML + JS sin frameworks, PWA (manifest + service worker) | La de la tesis, sin compilación; instalable en el teléfono |
| Servidor | Python 3.13, Starlette + Uvicorn (1 proceso) | Ligero; FastAPI se construye sobre Starlette |
| Modelo | `modelo/` (numpy, scipy) | Port fiel del notebook, compartido por servidor y scripts |
| Datos | SQLite en modo WAL (`datos/vocacional.db`) | Un archivo: respaldo y restauración triviales. Sobra para cientos de estudiantes y pocos usuarios simultáneos |
| Publicación | Docker Compose + Cloudflare Tunnel | HTTPS sin abrir puertos; el servidor no queda expuesto |

> ¿Por qué no PostgreSQL? Para un colegio (≈ 500 estudiantes, < 10 usuarios simultáneos) SQLite es más simple de
> operar y respaldar. El acceso a datos está concentrado en `servidor/bd.py` y `servidor/servicio.py` si algún día se migra.

## Módulos del notebook ↔ código

| Notebook | Código |
|---|---|
| 1.4 rúbrica, 1.8 cuadrantes | `modelo/constantes.py`, `modelo/bayes.py` |
| 3.3–3.11 notas → rendimiento | `modelo/notas.py` |
| 4.2–4.5 CHASIDE → evidencia, KR‑20 | `modelo/chaside.py` |
| 5.1–5.3 aprendizaje y posterior | `modelo/bayes.py`, `modelo/calibracion.py` |
| 7.1–7.3 carreras, Monte Carlo, razones | `modelo/carreras.py` |
| 9.1 contrato JSON | `modelo/resultado.py` |
| nombres ficticios | `modelo/nombres.py` (mismo algoritmo) |

**Calibración vs. inferencia.** Lo que el notebook aprende de la cohorte (normas de materias, normas de área y de
trayectoria, normas y KR‑20 del CHASIDE, α notas, λ, ρ, W_med, γ y normas de carreras) se guarda como una
*calibración* versionada en la tabla `calibraciones`. Cada estudiante se calcula al instante con la calibración
activa. Al instalar se usa la **calibración de referencia** (`config/calibracion_referencia.json`, construida con
`scripts/calibracion_referencia.py` desde las salidas oficiales de la tesis). *Recalibrar* aplica el notebook a los
datos del colegio con mínimos de seguridad (30 con notas, 30 con CHASIDE, 100 con ambos); lo que no alcanza el
mínimo se conserva de la calibración previa. Cada noche se recalculan todos (la antigüedad del CHASIDE cambia con el tiempo).

## Configuración editable (`datos/config/`)

Al primer arranque se copia `config/` al volumen de datos. Lo que el colegio cambie ahí sobrevive a las actualizaciones.

| Archivo | Para qué | Al cambiarlo |
|---|---|---|
| `mapeo_materias.csv` | Reglas regex materia → áreas y pesos (editable desde *Gestión → Materias*) | Se recalcula a todos |
| `chaside_preguntas.csv` | Texto de las 98 preguntas (`origen=oficial` al poner el texto real) | Inmediato |
| `claves_chaside.csv` | Ítem → área y escala | Requiere recalibrar |
| `carreras_EC.csv` | Catálogo de carreras (columnas C,H,A,S,I,D,E de 1 a 5) | γ y normas se recalculan solos con las posiciones guardadas de la cohorte |
| `fuentes.json` | Fichas de fuentes (α y criterios) | Reiniciar |

## Base de datos

`usuarios`, `estudiantes` (seudónimo `E-xxxxxx` + **HMAC** del ID del colegio, nunca el ID en claro), `calificaciones`
(solo 9.º–12.º), `chaside` (cada aplicación, con origen y anulación), `codigos` (solo el HMAC del código),
`resultados` (JSON del contrato de la tesis + entrada de índice), `calibraciones`, `cargas`, `trabajos`, `auditoria`, `ajustes`.

## API

| Ruta | Rol | Qué hace |
|---|---|---|
| `POST/DELETE /api/sesion`, `GET /api/yo`, `POST /api/yo/clave` | — | Sesión |
| `GET /datos/cohorte.json`, `/datos/carreras.json`, `/datos/estudiantes/{id}.json` | orientador | Mismo contrato que la tesis |
| `GET /api/estudiantes` · `PATCH /api/estudiantes/{id}` | orientador · admin | Lista con estado · editar |
| `POST/DELETE /api/estudiantes/{id}/chaside` | orientador | Registrar CHASIDE · anular el último |
| `POST /api/codigos` | orientador | Códigos para el test en línea |
| `POST /api/chaside/abrir`, `/api/chaside/enviar` | público (con código) | Test del estudiante |
| `POST /api/cargas/{notas,nomina,chaside}` · `GET /api/cargas` | admin | Archivos |
| `GET /api/materias` · `GET/PUT /api/config/mapeo` | orientador · admin | Materias y reglas |
| `GET /api/modelo` · `POST /api/modelo/{recalibrar,recalcular,activar/{id}}` | orientador · admin | Calibración |
| `GET /api/trabajos/{id}` | orientador | Progreso de tareas en segundo plano |
| `GET/POST /api/usuarios` · `PATCH /api/usuarios/{id}` · `GET /api/auditoria` | admin | Usuarios y bitácora |
| `GET/POST /api/respaldos` · `GET /api/exportar/resultados.csv` · `GET/PUT /api/ajustes` | admin | Operación |

## Seguridad

- Contraseñas con **scrypt** (biblioteca estándar); política mínima de 10 caracteres con mayúsculas, minúsculas y números.
- Sesión en cookie firmada `HttpOnly`, `Secure`, `SameSite=Strict`, 8 h; cambiar contraseña o rol cierra las sesiones.
- **CSRF:** toda escritura en `/api/` exige la cabecera `X-Vocacional: 1` (un sitio ajeno no puede enviarla sin CORS, que no se concede).
- Límite de intentos: 5 ingresos fallidos / 15 min por usuario+IP; 10 códigos inválidos / 15 min por IP.
- Cabeceras: CSP estricta (sin scripts en línea), `X-Frame-Options: DENY`, `nosniff`, `no-referrer`; `Cache-Control: no-store` en datos.
- `TrustedHostMiddleware`; IP real desde `CF-Connecting-IP` para la bitácora.
- Contenedor sin root, sistema de archivos de solo lectura, `cap_drop: ALL`, puerto publicado solo en `127.0.0.1`.
- Seudonimización: el ID del sistema académico se guarda solo como HMAC‑SHA256 con el secreto del servidor.
- Bitácora de ingresos, cargas, vistas de fichas, códigos, exportaciones y cambios de configuración.
- El service worker nunca guarda en caché `/api` ni `/datos`.

## Desarrollo

```bash
pip install -r requirements-dev.txt
VOCACIONAL_DATOS=./datos VOCACIONAL_COOKIE_SEGURA=false uvicorn servidor.app:app --reload
python pruebas/prueba_api.py http://localhost:8000 admin@x.ec Clave12345A orienta@x.ec Clave12345A
python scripts/calibracion_referencia.py RUTA/Vocacional_MIA      # regenera y valida la calibración de referencia
```
Al cambiar el modelo, actualizar también `web/motor.js` (recálculo en el navegador) y volver a correr ambas pruebas.
