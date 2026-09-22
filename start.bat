@echo off
chcp 65001 >nul 2>&1
title Business Helper - Lead Engine

echo ============================================
echo   Business Helper - Lead Generation Engine
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check .env
if not exist "%~dp0.env" (
    echo ERROR: .env file not found.
    echo Please create a .env file with your API keys.
    echo See .env.example for the required format.
    echo.
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "%~dp0.deps_installed" (
    echo Installing dependencies (first time only)...
    echo.
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo. > "%~dp0.deps_installed"
    echo.
)

:: Start the app
echo Starting the application...
echo The browser will open automatically.
echo.
echo To stop the application, close this window.
echo.
start http://localhost:8501
streamlit run "%~dp0app.py" --server.headless true
