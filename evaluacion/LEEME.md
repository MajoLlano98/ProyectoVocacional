# Evaluación del prototipo (v1.0 → v1.1)

Validación estadística de los ajustes al prototipo y comparación justa con el Random Forest.

| Archivo | Qué hace | Tiempo |
|---|---|---|
| `validacion_cruzada.py` | 3 simulaciones × 5 folds; Bayes v1.0, v1.1, ablaciones, RF base y RF ajustado; IC 95 % y pruebas pareadas | ~4 min |
| `sensibilidad.py` | Aprendizaje robusto (A2) y objetivo del umbral (0,90 / 0,92) en escenarios realista y estrés | ~1 min |
| `graficos.py` | `fig_folds.png` y `fig_umbral.png` a partir de los resultados | segundos |

```bash
pip install -r requirements-dev.txt
python evaluacion/validacion_cruzada.py && python evaluacion/sensibilidad.py && python evaluacion/graficos.py
```

Resultados en `resultados/`: `metricas_por_fold.csv` (todas las métricas de cada fold), `resumen_ic95.csv`,
`diferencias_pareadas.csv`, `curva_umbral.csv`, `umbral_por_fold.csv`, `rf_hiperparametros.csv`,
`sensibilidad_umbral_robusto.csv`.

**Datos:** notas reales de la cohorte de la tesis (seudónimos) y CHASIDE simulado con el generador del Módulo 3B,
que conoce la verdad. Las etiquetas se usan **solo para evaluar**; la red bayesiana nunca las ve.
Todos los modelos usan los mismos folds (comparación pareada). Semillas fijas: los resultados son reproducibles.
