@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo HLL Gunner SPA Calculate - kurulum / setup
echo.
set "PY="
set "TEMIZLE="

rem Onceki kurulum Python 3.12 ile yapildiysa sanal ortami yeniden kurma
rem If a previous setup used Python 3.12, keep the virtual environment
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))" 2>nul && goto paketler
  echo Onceki kurulum yarim ya da farkli Python surumuyle, yeniden kuruluyor...
  echo Previous setup is incomplete or used another Python version, reinstalling...
  set "TEMIZLE=--clear"
)

call :python_bul
if defined PY goto ortam

rem Python 3.12 yok: winget ile kullanici hesabina kur (yonetici izni gerekmez)
rem No Python 3.12: install it for this user with winget (no admin rights needed)
echo Python 3.12 bulunamadi, simdi otomatik kuruluyor (birkac dakika)...
echo Python 3.12 not found, installing it automatically (a few minutes)...
where winget >nul 2>nul || goto elle_kur
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
call :python_bul
if defined PY goto ortam

:elle_kur
echo.
echo Python 3.12 otomatik kurulamadi. Lutfen elle kurun:
echo   1. https://www.python.org/downloads/release/python-31210/ sayfasindaki "Files" tablosundan
echo      "Windows installer (64-bit)" dosyasini indirip calistirin.
echo   2. Ilk ekranda en alttaki "Add python.exe to PATH" kutusunu isaretleyin.
echo   3. Bitince KURULUM.bat'i yeniden calistirin.
echo.
echo Could not install Python 3.12 automatically. Please install it manually:
echo   1. From the "Files" table at https://www.python.org/downloads/release/python-31210/
echo      download and run "Windows installer (64-bit)".
echo   2. On the first screen tick "Add python.exe to PATH" at the bottom.
echo   3. Then run KURULUM.bat again.
pause
exit /b 1

:ortam
echo Python: %PY%
"%PY%" -m venv %TEMIZLE% .venv
if errorlevel 1 goto hata

:paketler
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto hata
".venv\Scripts\python.exe" modeli_indir.py
if errorlevel 1 goto hata
rem Kurulumun tamamlandigini isaretle: BASLAT.bat yarim kalan kurulumu buna bakarak anlar
rem Mark setup as complete: BASLAT.bat uses this to detect an interrupted setup
echo ok> ".venv\kurulum_tamam"
echo.
echo Kurulum tamam. BASLAT.bat ile acin.
echo Setup complete. Start with BASLAT.bat.
pause
exit /b 0

:hata
echo.
echo Kurulum basarisiz. Yukaridaki hata mesajina bakin. Internet baglantinizi kontrol edin.
echo Setup failed. See the error message above and check your internet connection.
pause
exit /b 1

rem PY: bulunan Python 3.12. Yeni kurulan Python bu pencerenin PATH'inde henuz gorunmez,
rem bu yuzden once bilinen kurulum klasorlerine bakilir.
rem A freshly installed Python is not on this window's PATH yet, so known folders are checked first.
:python_bul
set "PY="
for %%P in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%ProgramFiles%\Python312\python.exe") do (
  if not defined PY if exist %%P set "PY=%%~P"
)
if defined PY exit /b 0
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%P"
if defined PY exit /b 0
rem Microsoft Store'un sahte python.exe'si bir sey yazmaz, yanlislikla secilmez
rem The Microsoft Store python.exe stub prints nothing, so it is never picked by mistake
for /f "delims=" %%P in ('python -c "import sys; print(sys.executable if sys.version_info[:2] == (3, 12) else '')" 2^>nul') do set "PY=%%P"
exit /b 0
