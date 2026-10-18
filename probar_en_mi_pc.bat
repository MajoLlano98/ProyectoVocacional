@echo off
chcp 65001 >nul
title Sistema Vocacional - prueba local
cd /d "%~dp0"
echo.
echo  Sistema de Recomendacion Vocacional - PRUEBA LOCAL (datos ficticios)
echo  ====================================================================
where python >nul 2>nul
if errorlevel 1 (
  echo  No encuentro Python. Instala Python 3.13 desde https://www.python.org/downloads/
  echo  y en el instalador marca la casilla "Add python.exe to PATH". Luego vuelve a abrir este archivo.
  pause & exit /b 1
)
if not exist .venv (
  echo  Primera vez: preparando el entorno, tarda 1-3 minutos...
  python -m venv .venv || goto error
)
call .venv\Scripts\activate.bat
python -m pip install -q --disable-pip-version-check -r requirements.txt || goto error
set VOCACIONAL_DATOS=%~dp0datos_prueba
set VOCACIONAL_COOKIE_SEGURA=false
set VOCACIONAL_COLEGIO=Colegio de prueba
if not exist "%VOCACIONAL_DATOS%\vocacional.db" (
  echo  Creando usuarios y 40 estudiantes ficticios...
  python -m servidor.admin crear-usuario --usuario admin@prueba.ec --nombre "Administradora" --rol admin --clave Prueba12345 || goto error
  python -m servidor.admin crear-usuario --usuario orienta@prueba.ec --nombre "Orientadora" --rol orientador --clave Prueba12345 || goto error
  python -m servidor.admin demo || goto error
)
echo.
echo  LISTO. Se abrira el navegador en http://localhost:8000
echo    Usuario administracion:  admin@prueba.ec     clave: Prueba12345
echo    Usuario orientacion:     orienta@prueba.ec   clave: Prueba12345
echo    Test del estudiante:     http://localhost:8000/chaside
echo  Para detener el sistema cierra esta ventana.
echo.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000"
python -m uvicorn servidor.app:app --port 8000
exit /b 0
:error
echo.
echo  Algo fallo. Copia el mensaje de arriba y compartelo.
pause
exit /b 1
