@echo off
REM Build onedir : dist\Business\Business.exe
REM Python 3.x + PyInstaller + deps (voir req.txt). qt_common au meme niveau que MPayments.
REM
REM Si OSError WinError 145 (repertoire non vide) sur _internal\Python.framework : melange
REM d un ancien build macOS dans dist, ou partage Parallels\\Mac\Home. Supprimez manuellement
REM dist\Business, ou compilez depuis un disque local Windows (ex. C:\dev\MPayments).

cd /d "%~dp0"

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installez PyInstaller : pip install pyinstaller
    exit /b 1
)

if not exist "..\qt_common\src\Common" (
    echo Erreur : ..\qt_common\src\Common introuvable ^(clonez qt_common a cote de MPayments^).
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0clean_build_win.ps1"
if errorlevel 1 (
    echo.
    echo Si echec: sous macOS, Terminal dans le de^pot : rm -rf dist/Business dist/MPayments build/Mpayment_wind
    echo Puis lancez ce script depuis C:\  ^(copie du projet, hors partage Mac^).
    exit /b 1
)

pyinstaller --noconfirm Mpayment_wind.spec
if errorlevel 1 exit /b 1

echo.
echo OK — lancez : dist\Business\Business.exe
echo Donnees : database.db, LICENCE et .common_device_node a cote du .exe
echo Install NSIS cible : C:\Business
