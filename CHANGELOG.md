# Bitácora de cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) · versiones: [SemVer](https://semver.org/lang/es/).
Cada versión tiene su etiqueta en git (`git tag`); `git log --oneline` muestra el detalle commit a commit.

## [1.1.0] — 2026-10-20 · Ajustes al prototipo y validación estadística

### Cambiado
- **Umbral de certeza de las zonas calibrado sin etiquetas (A3).** Al recalibrar, el modelo elige el menor umbral
  cuya exactitud *esperada* (calculada con sus propias probabilidades) sea ≥ 90 %. Antes era fijo en 0,60.
  Con la cohorte de referencia elige 0,675. Validación cruzada: zonas asignadas correctas 86,0 % → 88,9 %
  (+2,9 pts, IC 95 % [2,5; 3,3], 15 de 15 folds), a cambio de más «indeterminado» (17,0 % → 26,5 %).
  Código: `modelo/bayes.py::elegir_umbral`, `modelo/calibracion.py` (paso 5), `modelo/constantes.py`.
- La calibración guardada pasa a `version: "1.1"` y registra el umbral elegido en `detalle.recalibrado.umbral`.
- `requirements-dev.txt`: versiones fijas de scikit-learn, pandas y matplotlib.

### Añadido
- `evaluacion/`: validación cruzada repetida (3 simulaciones × 5 folds) con IC 95 %, diferencias pareadas
  (Wilcoxon), ablaciones, curva del umbral y sensibilidad (escenarios realista y estrés).
- Protocolo de evaluación sin fuga de información (A1): KR-20, normas CHASIDE y normas de notas se calculan solo
  con el fold de entrenamiento. No cambia el servidor (ahí la calibración usa la cohorte sin etiquetas).
- Random Forest ajustado como alternativa justa: hiperparámetros por GridSearchCV interno + intervalos conformales.

### Evaluado y descartado
- **Aprendizaje robusto (A2)**: excluir aplicaciones con alerta de consistencia o incompletas al estimar λ y ρ.
  Sin efecto medible ni en el escenario realista ni en el de estrés (|Δ| < 0,001 en todas las métricas): la rúbrica
  de confiabilidad ya reduce el peso de esas aplicaciones. No se incorpora.

## [1.0.1] — 2026-10-18 · Alternativa evaluada
### Añadido
- `alternativa/`: Random Forest con las mismas entradas y salidas, comparación en el escenario del Módulo 3B,
  notebook y Colab autocontenido.

## [1.0.0] — 2026-10-18 · Primera versión para el colegio
### Añadido
- `modelo/`: port fiel del notebook de la tesis (módulos 3, 4, 5, 7 y 9), validado contra sus salidas.
- `servidor/` + `web/`: plataforma multiusuario (Starlette + SQLite), test CHASIDE como app (PWA), cargas de notas,
  recalibración versionada, bitácora de auditoría y respaldos.
- `despliegue/` (Docker + Cloudflare Tunnel), `docs/` (manual DECE, técnico, privacidad), `pruebas/` (35 verificaciones).
