@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Generer-les-documents.ps1" %*
if errorlevel 1 (
  echo.
  echo La generation a echoue. Consultez le message ci-dessus.
  pause
  exit /b 1
)
echo.
echo Documents disponibles dans le dossier exports a la racine du depot.
pause
