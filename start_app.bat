@echo off
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0"
if not exist "%PROJECT_ROOT%backend\venv\Scripts\python.exe" (
    set "PROJECT_ROOT=D:\AI-Course-Knowledge\"
)
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "BACKEND_PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe"
set "WEB_URL=http://127.0.0.1:5173"

echo ========================================
echo AI Course Knowledge - Start Application
echo ========================================
echo [PROJECT] %PROJECT_ROOT%

if not exist "%BACKEND_PYTHON%" (
    echo [ERROR] Backend virtual environment was not found.
    echo %BACKEND_PYTHON%
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] Frontend project was not found.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found. Install Node.js first.
    pause
    exit /b 1
)

netstat -ano -p tcp | findstr /R /C:":8000 .*LISTENING" >nul
if errorlevel 1 (
    echo [START] FastAPI backend: http://127.0.0.1:8000
    start "AI Course Backend" /min /D "%BACKEND_DIR%" cmd /k ""%BACKEND_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
) else (
    echo [SKIP] A service is already listening on port 8000.
)

netstat -ano -p tcp | findstr /R /C:":5173 .*LISTENING" >nul
if errorlevel 1 (
    if not exist "%FRONTEND_DIR%\node_modules" (
        echo [ERROR] Frontend dependencies are missing.
        echo Run npm install in the frontend directory first.
        pause
        exit /b 1
    )
    echo [START] Vite frontend: http://127.0.0.1:5173
    start "AI Course Frontend" /min /D "%FRONTEND_DIR%" cmd /k "npm run dev -- --host 127.0.0.1"
) else (
    echo [SKIP] A service is already listening on port 5173.
)

echo [WAIT] Checking service status...
powershell -NoProfile -Command "$deadline=(Get-Date).AddSeconds(30); do { try { $api=(Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/docs' -TimeoutSec 2).StatusCode -eq 200 } catch { $api=$false }; try { $web=(Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5173' -TimeoutSec 2).StatusCode -eq 200 } catch { $web=$false }; if ($api -and $web) { exit 0 }; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"

if errorlevel 1 (
    echo [ERROR] Services did not become ready within 30 seconds.
    echo Check the backend and frontend command windows.
    pause
    exit /b 1
)

echo [READY] Frontend and backend are running.
echo [WEB] %WEB_URL%
echo [API] http://127.0.0.1:8000/docs

if /I not "%~1"=="--no-browser" start "" "%WEB_URL%"
exit /b 0
