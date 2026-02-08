@echo off
REM uninstall.bat - Windows one-click uninstallation script
echo ================================================
echo   Traffic Client - Windows Uninstaller
echo ================================================

REM Check for administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Please run this script as Administrator.
    pause
    exit /b 1
)

echo Uninstalling Traffic Client service...
REM TODO: Implement service removal logic

echo Uninstallation complete.
pause
