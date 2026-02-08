@echo off
REM install.bat - Windows one-click installation script
echo ================================================
echo   Traffic Client - Windows Installer
echo ================================================

REM Check for administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Please run this script as Administrator.
    pause
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r "%~dp0..\requirements.txt"

echo Installation complete.
pause
