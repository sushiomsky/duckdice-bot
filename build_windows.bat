@echo off
REM Windows Build Script for DuckDice Bot Ultimate
REM Creates standalone .exe with all dependencies

echo ========================================================================
echo.
echo        DuckDice Bot Ultimate - Windows Build Script
echo.
echo ========================================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.7+ from python.org
    pause
    exit /b 1
)

echo Step 1: Installing dependencies...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies failed to install
)

echo.
echo Step 2: Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo Step 3: Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Step 4: Building Windows executable...
echo This may take 2-5 minutes...
echo.

pyinstaller --clean duckdice_gui_ultimate.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo.
echo      BUILD SUCCESSFUL!
echo.
echo ========================================================================
echo.

if exist "dist\DuckDiceBot.exe" (
    echo Executable created: dist\DuckDiceBot.exe
    echo.
    echo File size:
    dir dist\DuckDiceBot.exe | find "DuckDiceBot.exe"
    echo.
    echo You can now:
    echo   1. Run dist\DuckDiceBot.exe directly
    echo   2. Copy dist\DuckDiceBot.exe anywhere
    echo   3. Share with others (no Python needed!)
) else (
    echo WARNING: Executable not found at expected location
    echo Check dist\ folder for output files
)

echo.
echo ========================================================================
pause
