@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "BACKEND_PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "BACKEND_REQUIREMENTS=%BACKEND_DIR%\requirements.txt"
set "BACKEND_REQUIREMENTS_MARKER=%BACKEND_DIR%\.venv\.requirements-installed"

call :ensure_backend_env
if errorlevel 1 exit /b 1

call :ensure_frontend_env
if errorlevel 1 exit /b 1

start "Backend" powershell -NoExit -Command "Set-Location -LiteralPath '%BACKEND_DIR%'; & '%BACKEND_PYTHON%' main.py"
timeout /t 5 /nobreak >nul
start "Frontend Web" powershell -NoExit -Command "Set-Location -LiteralPath '%FRONTEND_DIR%'; npm run dev:web"

exit /b 0

:ensure_backend_env
if exist "%BACKEND_PYTHON%" goto install_backend_requirements

echo [setup] Creating backend virtual environment: %BACKEND_DIR%\.venv
call :select_python
if errorlevel 1 exit /b 1

%PYTHON_BOOTSTRAP% -m venv "%BACKEND_DIR%\.venv"
if errorlevel 1 (
  echo [error] Failed to create backend virtual environment.
  exit /b 1
)

:install_backend_requirements
if not exist "%BACKEND_REQUIREMENTS_MARKER%" goto run_pip_install
powershell -NoProfile -Command "if ((Get-Item -LiteralPath '%BACKEND_REQUIREMENTS%').LastWriteTime -gt (Get-Item -LiteralPath '%BACKEND_REQUIREMENTS_MARKER%').LastWriteTime) { exit 1 }"
if errorlevel 1 goto run_pip_install
exit /b 0

:run_pip_install
echo [setup] Installing backend dependencies from requirements.txt
"%BACKEND_PYTHON%" -m pip install -r "%BACKEND_REQUIREMENTS%"
if errorlevel 1 (
  echo [error] Backend dependency installation failed.
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
echo [error] Python 3.11+ was not found. Install Python 3.11 and make it available as "py -3.11" or "python".
exit /b 1

:python_version_unsupported
echo [error] The available "python" is older than 3.11. Install Python 3.11 or run "py -3.11" from PATH.
exit /b 1

:ensure_frontend_env
where npm >nul 2>nul
if errorlevel 1 (
  echo [error] npm was not found. Install Node.js LTS and reopen this terminal.
  exit /b 1
)

if exist "%FRONTEND_DIR%\node_modules" exit /b 0

pushd "%FRONTEND_DIR%"
if errorlevel 1 (
  echo [error] Failed to enter frontend directory: %FRONTEND_DIR%
  exit /b 1
)

if exist package-lock.json (
  echo [setup] Installing frontend dependencies with npm ci
  npm ci
) else (
  echo [setup] Installing frontend dependencies with npm install
  npm install
)
set "NPM_INSTALL_EXIT=%ERRORLEVEL%"
popd

if not "%NPM_INSTALL_EXIT%"=="0" (
  echo [error] Frontend dependency installation failed.
  exit /b 1
)
exit /b 0
