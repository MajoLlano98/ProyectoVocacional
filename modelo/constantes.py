"""Constantes del modelo (Módulos 1, 3, 5 y 7 del notebook)."""

EJES = {
    "C": "Administrativas y Contables",
    "H": "Humanísticas y Ciencias Sociales",
    "A": "Artísticas",
    "S": "Ciencias de la Salud",
    "I": "Ingenierías, Técnicas y Computación",
    "D": "Defensa y Seguridad",
    "E": "Ciencias Exactas y Agrarias",
}
CODIGOS = list(EJES)                       # orden fijo: C H A S I D E
TIPOS_CHASIDE = ("interes", "aptitud")

# Módulo 1.4 · rúbrica de criterios cualitativos → factor que multiplica la varianza
RUBRICA = {
    "validacion": {"publicada": 1.0, "adaptacion": 1.3, "ad_hoc": 2.0},
    "equivalencia": {"directa": 1.0, "aproximada": 1.5, "debil": 2.5},
    "antiguedad": {"menos_1_anio": 1.0, "1_a_2_anios": 1.2, "mas_2_anios": 1.5},
    "completitud": {"completa": 1.0, "parcial": 1.3, "incompleta": 2.0},
    "modalidad": {"supervisada": 1.0, "autonoma": 1.2},
    "consistencia": {"sin_alertas": 1.0, "alerta": 2.0},
}

# Módulo 1.8 · zonas del plano
UMBRAL_CERTEZA = 0.60
ZONAS = ("vocacion_consolidada", "interes_a_fortalecer", "talento_no_explorado", "no_prioritaria")
TEXTO_ZONA = {
    "vocacion_consolidada": "Vocación consolidada", "interes_a_fortalecer": "Interés a fortalecer",
    "talento_no_explorado": "Talento no explorado", "no_prioritaria": "Área no prioritaria",
    "indeterminado": "Indeterminado: falta evidencia",
}
TEXTO_AUTO = {"por_encima": "se percibe por ENCIMA de sus notas", "por_debajo": "se percibe por DEBAJO de sus notas",
              "coherente": "coherente con sus notas"}

# Módulo 3 · notas
GRADOS_SECUNDARIA = (9, 10, 11, 12)
N_MIN_MATERIA = 5          # mínimo de estudiantes para estandarizar contra materia×grado
GAMMA_ANIOS = 0.8          # decaimiento por año hacia atrás

# Módulo 5 · aprendizaje
FRACCION_ENTRENAMIENTO = 0.7
SEMILLA_PARTICION = 7

# Módulo 7 · carreras
BETA_INTERES = 0.50
N_SIM = 1000
TOP_K = 5
N_EXPORTAR = 10
GAMMAS_CANDIDATOS = (1, 1.5, 2, 3, 4)
TV_MAX = 0.10
SEMILLA_MC = 20261004

VERSION_CONTRATO = "1.0"
