@echo off
title Build TeklaHelper

:menu
cls
echo ================================================
echo   BUILD TEKLA MONITOR
echo ================================================
echo.
echo Choisissez le type de build:
echo [1] Build simple (PyInstaller + metadata)
echo [2] Build obfusque (PyArmor + PyInstaller + metadata)
echo [3] Generer fichier version_info.txt
echo [4] Quitter
echo.
set /p choice="Votre choix (1-4): "

if "%choice%"=="1" goto build_simple
if "%choice%"=="2" goto build_obfuscated
if "%choice%"=="3" goto create_version_info
if "%choice%"=="4" exit
goto menu

:create_version_info
cls
echo [CREATION VERSION_INFO.TXT]
echo.
echo Création du fichier de métadonnées...

(
echo VSVersionInfo^(
echo   ffi=FixedFileInfo^(
echo     filevers=^(2, 0, 0, 0^),
echo     prodvers=^(2, 0, 0, 0^),
echo     mask=0x3f,
echo     flags=0x0,
echo     OS=0x40004,
echo     fileType=0x1,
echo     subtype=0x0,
echo     date=^(0, 0^)
echo   ^),
echo   kids=[
echo     StringFileInfo^(
echo       [
echo       StringTable^(
echo         u'040904B0',
echo         [StringStruct^(u'CompanyName', u'Tekla Corporation'^),
echo         StringStruct^(u'FileDescription', u'Tekla Productivity Helper'^),
echo         StringStruct^(u'FileVersion', u'2.0.0.0'^),
echo         StringStruct^(u'InternalName', u'TeklaHelper'^),
echo         StringStruct^(u'LegalCopyright', u'Copyright ^(C^) 2024'^),
echo         StringStruct^(u'OriginalFilename', u'TeklaHelper.exe'^),
echo         StringStruct^(u'ProductName', u'Tekla Productivity Tools'^),
echo         StringStruct^(u'ProductVersion', u'2.0.0.0'^)]^)
echo       ]^),
echo     VarFileInfo^([VarStruct^(u'Translation', [1033, 1200]^)]^)
echo   ]
echo ^)
) > version_info.txt

echo.
echo ================================================
echo   version_info.txt cree avec succes !
echo ================================================
pause
goto menu

:build_simple
cls
echo [BUILD SIMPLE AVEC METADATA]
echo.

REM Vérifier si version_info.txt existe
if not exist version_info.txt (
    echo Creation automatique de version_info.txt...
    call :create_version_info_silent
)

REM Vérifier si icon.ico existe
if not exist icon.ico (
    echo ATTENTION: icon.ico introuvable !
    echo Le build continuera sans icone personnalisee.
    echo.
    set ICON_PARAM=
) else (
    set ICON_PARAM=--icon=icon.ico
)

echo [1/3] Nettoyage...
rmdir /s /q build dist __pycache__ 2>nul
del /q *.spec 2>nul

echo [2/3] Compilation avec PyInstaller...
pyinstaller --onefile ^
    --noconsole ^
    --name "TeklaHelper" ^
    --version-file=version_info.txt ^
    %ICON_PARAM% ^
    monitor.py

echo [3/3] Finalisation...
if exist dist\TeklaHelper.exe (
    move dist\TeklaHelper.exe TeklaHelper.exe
    rmdir /s /q build dist 2>nul
    del /q *.spec 2>nul
    echo.
    echo ================================================
    echo   BUILD TERMINE !
    echo   Fichier: TeklaHelper.exe
    echo   Localisation: %CD%
    echo ================================================
) else (
    echo ERREUR: Build echoue
)
pause
goto menu

:build_obfuscated
cls
echo [BUILD OBFUSQUE AVEC METADATA]
echo.

REM Vérifier version_info.txt
if not exist version_info.txt (
    echo Creation automatique de version_info.txt...
    call :create_version_info_silent
)

REM Vérifier icon.ico
if not exist icon.ico (
    echo ATTENTION: icon.ico introuvable !
    set ICON_PARAM=
) else (
    set ICON_PARAM=--icon=icon.ico
)

echo [1/5] Nettoyage...
rmdir /s /q build dist __pycache__ output 2>nul
del /q *.spec 2>nul

echo [2/5] Obfuscation avec PyArmor...
pyarmor gen --enable-jit --mix-str monitor.py
if not exist dist\monitor.py (
    echo ERREUR: PyArmor a echoue
    pause
    goto menu
)

echo [3/5] Compilation avec PyInstaller...
pyinstaller --onefile ^
    --noconsole ^
    --name "TeklaHelper" ^
    --version-file=version_info.txt ^
    %ICON_PARAM% ^
    --distpath=output ^
    --workpath=build ^
    dist\monitor.py

echo [4/5] Finalisation...
if exist output\TeklaHelper.exe (
    move output\TeklaHelper.exe TeklaHelper.exe
    echo Succes !
) else (
    echo ERREUR: Compilation echouee
)

echo [5/5] Nettoyage...
rmdir /s /q build dist __pycache__ output 2>nul
del /q *.spec 2>nul

echo.
echo ================================================
echo   BUILD TERMINE !
echo   Fichier: TeklaHelper.exe
echo   Localisation: %CD%
echo ================================================
pause
goto menu

:create_version_info_silent
REM Création silencieuse du fichier version_info.txt
(
echo VSVersionInfo^(
echo   ffi=FixedFileInfo^(
echo     filevers=^(2, 0, 0, 0^),
echo     prodvers=^(2, 0, 0, 0^),
echo     mask=0x3f,
echo     flags=0x0,
echo     OS=0x40004,
echo     fileType=0x1,
echo     subtype=0x0,
echo     date=^(0, 0^)
echo   ^),
echo   kids=[
echo     StringFileInfo^(
echo       [
echo       StringTable^(
echo         u'040904B0',
echo         [StringStruct^(u'CompanyName', u'Tekla Corporation'^),
echo         StringStruct^(u'FileDescription', u'Tekla Productivity Helper'^),
echo         StringStruct^(u'FileVersion', u'2.0.0.0'^),
echo         StringStruct^(u'InternalName', u'TeklaHelper'^),
echo         StringStruct^(u'LegalCopyright', u'Copyright ^(C^) 2024'^),
echo         StringStruct^(u'OriginalFilename', u'TeklaHelper.exe'^),
echo         StringStruct^(u'ProductName', u'Tekla Productivity Tools'^),
echo         StringStruct^(u'ProductVersion', u'2.0.0.0'^)]^)
echo       ]^),
echo     VarFileInfo^([VarStruct^(u'Translation', [1033, 1200]^)]^)
echo   ]
echo ^)
) > version_info.txt
exit /b

:end
exit