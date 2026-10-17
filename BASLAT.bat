@echo off
cd /d "%~dp0"
rem Ilk acilista ya da kurulum yarim kaldiysa (ornegin model inerken pencere kapandiysa) kurulumu yeniden yapar
rem Runs the setup on first start, or again if it was interrupted (e.g. window closed during the model download)
if not exist ".venv\kurulum_tamam" (
  call KURULUM.bat
  if not exist ".venv\kurulum_tamam" exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" uygulama.py
