# Sistema de Recomendación Vocacional · imagen del servidor
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    VOCACIONAL_DATOS=/datos TZ=America/Guayaquil

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código y configuración de fábrica (los datos y la configuración editable viven en el volumen /datos)
COPY modelo/ modelo/
COPY servidor/ servidor/
COPY web/ web/
COPY config/ config/
COPY pruebas/datos/reporte_ejemplo.csv pruebas/datos/reporte_ejemplo.csv

# Usuario sin privilegios
RUN useradd --create-home --uid 1000 vocacional && mkdir -p /datos && chown -R vocacional:vocacional /datos
USER vocacional

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/salud', timeout=4).status==200 else 1)"

# Un solo proceso: los trabajos en segundo plano y el respaldo nocturno corren dentro de él
CMD ["uvicorn", "servidor.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header", "--timeout-graceful-shutdown", "20"]
