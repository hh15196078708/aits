@echo off
REM =============================================================================
REM 跨平台Python客户端 - Windows启动脚本
REM =============================================================================
REM 
REM 功能:
REM   1. 检查Python环境
REM   2. 自动安装依赖
REM   3. 设置UTF-8编码
REM   4. 启动客户端程序
REM
REM 使用方法:
REM   双击运行或在命令行执行: client_start.bat
REM =============================================================================

REM 设置控制台编码为UTF-8，避免中文乱码
chcp 65001 >nul 2>&1

REM 设置Python IO编码
set PYTHONIOENCODING=utf-8

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 显示启动信息
echo =============================================================================
echo                   跨平台Python客户端 - Windows
echo =============================================================================
echo.

REM -----------------------------------------------------------------------------
REM 步骤1: 检查Python是否安装
REM -----------------------------------------------------------------------------
echo [1/4] 检查Python环境...

REM 尝试使用python命令
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :python_found
)

REM 尝试使用py命令（Python Launcher）
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :python_found
)

REM 尝试使用python3命令
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :python_found
)

REM Python未找到
echo [错误] 未找到Python，请先安装Python 3.6或更高版本
echo        下载地址: https://www.python.org/downloads/
pause
exit /b 1

:python_found
echo        找到Python: %PYTHON_CMD%
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do echo        版本: %%i

REM -----------------------------------------------------------------------------
REM 步骤2: 检查并安装基础依赖
REM -----------------------------------------------------------------------------
echo.
echo [2/4] 检查并安装依赖...

REM 升级pip（静默）
%PYTHON_CMD% -m pip install --upgrade pip -q >nul 2>&1

REM 安装基础依赖
%PYTHON_CMD% -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo        [警告] 部分依赖安装失败，尝试单独安装...
    %PYTHON_CMD% -m pip install psutil -q
    %PYTHON_CMD% -m pip install pycryptodome -q
    %PYTHON_CMD% -m pip install requests -q
)

echo        基础依赖安装完成

REM -----------------------------------------------------------------------------
REM 步骤3: 安装Windows专属依赖
REM -----------------------------------------------------------------------------
echo.
echo [3/4] 安装Windows专属依赖...

REM 检查pywin32是否已安装
%PYTHON_CMD% -c "import win32api" >nul 2>&1
if %errorlevel% neq 0 (
    echo        正在安装pywin32...
    %PYTHON_CMD% -m pip install pywin32 -q
    if %errorlevel% neq 0 (
        echo        [警告] pywin32安装失败，部分功能可能受限
    )
) else (
    echo        pywin32已安装
)

REM 检查wmi是否已安装
%PYTHON_CMD% -c "import wmi" >nul 2>&1
if %errorlevel% neq 0 (
    echo        正在安装wmi...
    %PYTHON_CMD% -m pip install wmi -q
    if %errorlevel% neq 0 (
        echo        [警告] wmi安装失败，部分功能可能受限
    )
) else (
    echo        wmi已安装
)

echo        Windows专属依赖安装完成

REM -----------------------------------------------------------------------------
REM 步骤4: 启动客户端
REM -----------------------------------------------------------------------------
echo.
echo [4/4] 启动客户端...
echo =============================================================================
echo.

REM 启动主程序
%PYTHON_CMD% main.py

REM 程序退出后暂停，显示退出信息
echo.
echo =============================================================================
echo 客户端已退出
echo =============================================================================
pause
