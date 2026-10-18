"""
Vocacional Bayesiano — motor del modelo.

Port fiel del notebook de la tesis (tesis/notebook/VocacionalBayesiano.ipynb), módulos 3, 4, 5, 7 y 9.
Lo usan el servidor (inferencia por estudiante + recalibración de la cohorte) y los scripts.
Validado contra las salidas oficiales del notebook: ver pruebas/validar_contra_tesis.py.
"""
from .constantes import CODIGOS, EJES  # noqa: F401

__version__ = "1.0.0"
