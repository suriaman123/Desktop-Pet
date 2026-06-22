@echo off
title Yorkie Desktop Pet
echo ==========================================
echo       🐾  Yorkie Desktop Pet  🐾
echo ==========================================
echo.
echo Starting your Yorkshire Terrier...
echo.
echo Controls:
echo   Left-click  : Woof! + count
echo   Right-click : Menu (Roam Mode, Feed, Reset, Close)
echo   Drag        : Move pet anywhere on screen
echo   Any key     : Adds to activity count
echo.

:: Try Python from PATH first
python yorkie_pet.py 2>nul
if %errorlevel% neq 0 (
    :: Try py launcher (Windows Python installer default)
    py yorkie_pet.py 2>nul
    if %errorlevel% neq 0 (
        echo ERROR: Python not found!
        echo Please install Python from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during install.
        pause
    )
)
