# Sistema de Recomendación Vocacional Bayesiano

Plataforma de orientación vocacional para el DECE: combina las **notas del colegio** y el **test CHASIDE** con un
modelo bayesiano para estimar, en cada una de las 7 áreas vocacionales, cuánto le **interesa** al estudiante y qué
tan bien **rinde**, con su incertidumbre, y propone **carreras afines** del Ecuador.

Proyecto de la Maestría en Inteligencia Artificial Aplicada (UDLA). El modelo es el del notebook de la tesis
(`tesis/notebook/`), llevado a un servidor web que el colegio puede operar por su cuenta.

```
                 Internet  →  https://vocacional.colegio.edu.ec
                                        │
                          Cloudflare (HTTPS + control de acceso)
                                        │ túnel cifrado (sin abrir puertos)
┌──────────────────────────── SERVIDOR (Docker) ─┴───────────────────────────────┐
│  web/        panel del DECE + test CHASIDE para el teléfono (instalable)       │
│  servidor/   API, sesiones y roles, cargas, códigos, trabajos, bitácora        │
│  modelo/     notas → evidencia · CHASIDE → evidencia · posterior · carreras    │
│  datos/      SQLite + configuración editable + respaldos diarios               │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Cómo funciona para el colegio

1. **Administración** sube el reporte de notas del sistema académico (CSV o Excel).
2. **El DECE** genera un código por estudiante; cada uno responde el CHASIDE en su teléfono (o en papel y se registra).
3. **El servidor calcula al instante**: zona de cada área (vocación consolidada, interés a fortalecer, talento no
   explorado, no prioritaria o indeterminado), plano interés × rendimiento, top de carreras con su estabilidad y alertas.
4. Al inicio de cada año lectivo, **recalibra** el modelo con los datos propios del colegio (un botón).

Manual para el DECE: [`docs/MANUAL_DECE.md`](docs/MANUAL_DECE.md) · Instalación: [`despliegue/GUIA_INSTALACION.md`](despliegue/GUIA_INSTALACION.md)

## Estructura

```
vocacional/
├── modelo/           motor del modelo (port fiel del notebook, validado contra sus salidas)
├── servidor/         aplicación web (Starlette + SQLite): API, seguridad, cargas, respaldos, comandos
├── web/              interfaz: panel del DECE, gestión, ingreso, test CHASIDE para estudiantes, PWA
├── config/           valores de fábrica: mapeo de materias, claves y preguntas CHASIDE, fuentes,
│                     carreras_EC.csv y calibración de referencia de la tesis
├── despliegue/       guía de instalación, actualización y respaldo externo
├── docs/             manual del DECE, manual técnico y privacidad
├── pruebas/          prueba de punta a punta de la API y datos de ejemplo ficticios
├── scripts/          construcción y validación de la calibración de referencia
├── tesis/            notebook de la tesis (sin modificar) y encuesta de validación con universitarios
├── Dockerfile, docker-compose.yml, .env.ejemplo
└── datos/            ⚠ NO se versiona: base de datos, configuración editable y respaldos
```

## Probar en tu computador (sin Docker)

**Lo más fácil:** doble clic en `probar_en_mi_pc.bat` (Windows) o `bash probar_en_mi_pc.sh` (Mac/Linux). Necesita Python 3.13.
Abre http://localhost:8000 con `admin@prueba.ec` / `Prueba12345` (datos ficticios).

A mano:

```bash
pip install -r requirements-dev.txt
export VOCACIONAL_DATOS=./datos VOCACIONAL_COOKIE_SEGURA=false
python -m servidor.admin crear-usuario --usuario admin@prueba.ec --nombre "Admin" --rol admin
python -m servidor.admin demo                 # 40 estudiantes ficticios con CHASIDE simulado
uvicorn servidor.app:app --port 8000          # abrir http://localhost:8000
```

## En producción

```bash
cp .env.ejemplo .env      # completar secreto, dominio y token del túnel
docker compose up -d --build
docker compose exec app python -m servidor.admin crear-usuario --usuario dece@colegio.edu.ec --nombre "…" --rol admin
```
Detalle paso a paso: [`despliegue/GUIA_INSTALACION.md`](despliegue/GUIA_INSTALACION.md).

## Fidelidad con la tesis

`scripts/calibracion_referencia.py` reconstruye la calibración desde las salidas oficiales del notebook y compara
cada etapa (sobre los 500 estudiantes de la cohorte de referencia):

| Etapa | Diferencia máxima con el notebook |
|---|---|
| Rendimiento por área (Módulo 3) | 0.0007 · `W_efectiva` exacto |
| Parámetros aprendidos α, λ, ρ (5.2) | 0.0005 |
| Posterior μ, σ (5.3) | 0.0008 · 0.00001 |
| Zonas | 3 499 de 3 500 idénticas |
| γ de carreras / normas de afinidad (7.2) | 3.0 igual · 0.0006 |

Las diferencias vienen del redondeo a 3 decimales de las notas exportadas. P(top 5) usa el mismo generador aleatorio
que la interfaz (`motor.js`), de modo que servidor y navegador coinciden.

## Pruebas

```bash
python pruebas/prueba_api.py http://localhost:8000 ADMIN CLAVE ORIENTADOR CLAVE    # 35 verificaciones (sobre una instancia vacía)
python scripts/calibracion_referencia.py RUTA/Vocacional_MIA                         # fidelidad con la tesis
```

## Licencia y créditos

Ver `LICENSE`. Modelo: tesis de la Maestría en IA Aplicada (UDLA). Preguntas del CHASIDE incluidas: **prototipo
de redacción propia**; para uso real el DECE debe cargar el texto oficial en `config/chaside_preguntas.csv`.
