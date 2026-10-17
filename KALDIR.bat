@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo HLL Gunner SPA Calculate - kaldirma / uninstall
echo.
echo Silinecekler / Will be deleted:
echo   1. Bu klasordeki Python ortami (.venv) / the Python environment in this folder
echo   2. Indirilen ses modelleri / downloaded speech models: %LOCALAPPDATA%\HLLGunner
echo Program dosyalari ve ayarlar.json kalir. Python 3.12'nin kendisi kaldirilmaz.
echo Program files and ayarlar.json stay. Python 3.12 itself is not removed.
echo.
echo Not: Sadece yeniden kurmak istiyorsaniz bunu calistirmayin; KURULUM.bat eksikleri kendisi onarir
echo ve ses modelini yeniden indirmez.
echo Note: to reinstall, do not run this; KURULUM.bat repairs what is missing and keeps the model.
echo.
choice /C EH /M "Silinsin mi? E=evet/yes H=hayir/no"
if errorlevel 2 exit /b 0
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq HLL Gunner*" >nul 2>nul
if exist ".venv" rmdir /s /q ".venv"
if exist "%LOCALAPPDATA%\HLLGunner" rmdir /s /q "%LOCALAPPDATA%\HLLGunner"
echo Silindi. / Deleted.
pause
