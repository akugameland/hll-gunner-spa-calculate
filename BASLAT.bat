@echo off
cd /d "%~dp0"
rem Ilk acilista kurulumu kendisi yapar / Runs the setup by itself on first start
if not exist ".venv\Scripts\pythonw.exe" (
  call KURULUM.bat
  if not exist ".venv\Scripts\pythonw.exe" exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" uygulama.py
