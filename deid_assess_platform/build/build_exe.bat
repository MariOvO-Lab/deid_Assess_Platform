@echo off

REM Build script for deid_assess_tool

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)

REM Check if pip is available
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: pip not found. Please ensure Python is installed correctly.
    pause
    exit /b 1
)

REM Install dependencies with Tsinghua mirror
echo Installing dependencies...
pip install --user -i https://pypi.tuna.tsinghua.edu.cn/simple -r ..\requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

REM Install PyInstaller with Tsinghua mirror
echo Installing PyInstaller...
pip install --user -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller
if %errorlevel% neq 0 (
    echo Error: Failed to install PyInstaller.
    pause
    exit /b 1
)

REM Create dist directory if it doesn't exist
if not exist dist mkdir dist

REM Build the application
echo Building application...
pyinstaller --onefile --windowed --name deid_assess_tool ..\main.py
if %errorlevel% neq 0 (
    echo Error: Failed to build application.
    pause
    exit /b 1
)

REM Copy configuration files and templates
echo Copying configuration files and templates...

if not exist dist\config mkdir dist\config
if not exist dist\templates mkdir dist\templates
if not exist dist\data mkdir dist\data

if exist ..\config\rules.json (
    copy ..\config\rules.json dist\config\
)

if exist ..\templates\* (
    copy ..\templates\* dist\templates\
)

echo Build completed! Executable is located in the dist directory
pause