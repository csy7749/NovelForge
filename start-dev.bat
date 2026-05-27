@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "BACKEND_PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "BACKEND_REQUIREMENTS=%BACKEND_DIR%\requirements.txt"
set "BACKEND_REQUIREMENTS_MARKER=%BACKEND_DIR%\.venv\.requirements-installed"
set "STARTUP_LOG=%ROOT_DIR%start-dev.log"
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

> "%STARTUP_LOG%" (
  echo NovelForge startup log
  echo Time: %DATE% %TIME%
  echo Root: %ROOT_DIR%
)

call :ensure_powershell_env
if errorlevel 1 goto startup_failed

call :ensure_backend_env
if errorlevel 1 goto startup_failed

call :ensure_frontend_env
if errorlevel 1 goto startup_failed

call :log "[start] Launching backend window"
start "Backend" "%POWERSHELL_EXE%" -NoExit -Command "Set-Location -LiteralPath '%BACKEND_DIR%'; & '%BACKEND_PYTHON%' main.py"
timeout /t 5 /nobreak >nul
call :log "[start] Launching frontend web window"
start "Frontend Web" "%POWERSHELL_EXE%" -NoExit -Command "Set-Location -LiteralPath '%FRONTEND_DIR%'; npm run dev:web"

exit /b 0

:startup_failed
echo.
echo [error] NovelForge startup failed. Review the error above.
echo [hint] Common causes: missing Python 3.11+, missing Node.js/npm, or dependency installation failure.
echo [log] Detailed startup log: %STARTUP_LOG%
echo.
pause
exit /b 1

:log
echo %~1
>> "%STARTUP_LOG%" echo %~1
exit /b 0

:ensure_powershell_env
if exist "%POWERSHELL_EXE%" exit /b 0
call :log "[error] Windows PowerShell was not found at: %POWERSHELL_EXE%"
exit /b 1

:ensure_backend_env
if exist "%BACKEND_PYTHON%" goto install_backend_requirements

call :log "[setup] Creating backend virtual environment: %BACKEND_DIR%\.venv"
call :log "[log] Command output is being written to: %STARTUP_LOG%"
call :select_python
if errorlevel 1 exit /b 1

%PYTHON_BOOTSTRAP% -m venv "%BACKEND_DIR%\.venv" >> "%STARTUP_LOG%" 2>&1
if errorlevel 1 (
  call :log "[error] Failed to create backend virtual environment."
  exit /b 1
)

:install_backend_requirements
if not exist "%BACKEND_REQUIREMENTS_MARKER%" goto run_pip_install
"%POWERSHELL_EXE%" -NoProfile -Command "if ((Get-Item -LiteralPath '%BACKEND_REQUIREMENTS%').LastWriteTime -gt (Get-Item -LiteralPath '%BACKEND_REQUIREMENTS_MARKER%').LastWriteTime) { exit 1 }" >> "%STARTUP_LOG%" 2>&1
if errorlevel 1 goto run_pip_install
exit /b 0

:run_pip_install
call :log "[setup] Installing backend dependencies from requirements.txt"
call :log "[log] Command output is being written to: %STARTUP_LOG%"
"%BACKEND_PYTHON%" -m pip install -r "%BACKEND_REQUIREMENTS%" >> "%STARTUP_LOG%" 2>&1
if errorlevel 1 (
  call :log "[error] Backend dependency installation failed."
  exit /b 1
)
type nul > "%BACKEND_REQUIREMENTS_MARKER%"
exit /b 0

:select_python
where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_BOOTSTRAP=py -3.11"
    exit /b 0
  )
)

where python >nul 2>nul
if errorlevel 1 goto python_missing

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 goto python_version_unsupported

set "PYTHON_BOOTSTRAP=python"
exit /b 0

:python_missing
call :log "[error] Python 3.11+ was not found. Install Python 3.11 and make it available as py -3.11 or python."
exit /b 1

:python_version_unsupported
call :log "[error] The available python is older than 3.11. Install Python 3.11 or run py -3.11 from PATH."
exit /b 1

:ensure_frontend_env
where npm >nul 2>nul
if errorlevel 1 (
  call :log "[error] npm was not found. Install Node.js LTS and reopen this terminal."
  exit /b 1
)

if exist "%FRONTEND_DIR%\node_modules" exit /b 0

pushd "%FRONTEND_DIR%"
if errorlevel 1 (
  call :log "[error] Failed to enter frontend directory: %FRONTEND_DIR%"
  exit /b 1
)

if exist package-lock.json (
  call :log "[setup] Installing frontend dependencies with npm ci"
  call :log "[log] Command output is being written to: %STARTUP_LOG%"
  npm ci >> "%STARTUP_LOG%" 2>&1
) else (
  call :log "[setup] Installing frontend dependencies with npm install"
  call :log "[log] Command output is being written to: %STARTUP_LOG%"
  npm install >> "%STARTUP_LOG%" 2>&1
)
set "NPM_INSTALL_EXIT=%ERRORLEVEL%"
popd

if not "%NPM_INSTALL_EXIT%"=="0" (
  call :log "[error] Frontend dependency installation failed."
  exit /b 1
)
exit /b 0
