# Alternativa evaluada: Random Forest vs. red bayesiana

Comparación pedida para la tesis: se construye la alternativa más común (Random Forest, aprendizaje supervisado) con
las mismas entradas y salidas que la red bayesiana del proyecto, y se evalúan ambas en el escenario del Módulo 3B.

| Archivo | Qué es |
|---|---|
| `Alternativa_RandomForest.ipynb` | Notebook paso a paso (producto de la alternativa + comparación + un estudiante con ambos modelos) |
| `comparacion.py` | El mismo análisis como script: `python alternativa/comparacion.py` (~1 min) |
| `graficos.py` | Genera las figuras desde `resultados/resumen.json` |
| `resultados/` | Tabla comparativa, curva de aprendizaje, predicciones y figuras |

Resultado: precisión equivalente (la red bayesiana reproduce exactamente las métricas oficiales de la tesis), pero la
red bayesiana no necesita etiquetas, su rango del 90 % se cumple (88–91 % vs 68–69 %), su Brier es menor (0,25 vs
0,28) y es estable con pocos datos (0,25 vs 0,40 con 20 estudiantes). Requiere `scikit-learn` y `pandas`.
