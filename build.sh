@echo off
echo ================================================
echo   BUILD TEKLA MONITOR - VERSION OBFUSQUEE
echo ================================================

echo.
echo [1/4] Nettoyage...
rmdir /s /q build dist __pycache__ 2>nul

echo [2/4] Obfuscation avec PyArmor...
pyarmor gen --enable-jit --mix-str monitor.py

echo [3/4] Compilation avec PyInstaller...
cd dist
pyinstaller --onefile ^
    --noconsole ^
    --name "TeklaHelper" ^
    --version-file=../version_info.txt ^
    --icon=../icon.ico ^
    monitor.py

echo [4/4] Nettoyage final...
cd ..
move dist\\dist\\TeklaHelper.exe TeklaHelper.exe
rmdir /s /q dist\\dist dist\\build dist\\__pycache__

echo.
echo ================================================
echo   BUILD TERMINE !
echo   Fichier: TeklaHelper.exe
echo ================================================
pause