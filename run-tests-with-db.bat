@echo off
REM EDI 835 Parser - Test Runner for Windows
REM Usage: run-tests-with-db.bat [--keep-data]

setlocal enabledelayedexpansion

REM Parse arguments
set KEEP_DATA=

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--keep-data" set KEEP_DATA=--keep-data
shift
goto parse_args
:args_done

echo.
echo ========================================
echo EDI 835 Parser - Test Runner
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please create .env with database connection parameters.
    echo Required: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA
    exit /b 1
)

echo [OK] Found .env configuration file

REM Load environment variables from .env
echo.
echo Loading database configuration...
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" (
        if not "%%a"=="" (
            set "%%a=%%b"
            echo    Set %%a
        )
    )
)

echo [OK] Configuration loaded

REM Activate virtual environment
echo.
echo Activating Python virtual environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated (.venv^)
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated (venv^)
) else (
    echo [INFO] No virtual environment found (.venv or venv^)
    echo Proceeding with system Python...
)

REM Run tests
echo.
echo ========================================
echo Running tests with database
echo ========================================
echo.

if "%KEEP_DATA%"=="--keep-data" (
    echo Running with --keep-data flag (data will not be cleared^)
    python test_with_db.py --keep-data
) else (
    python test_with_db.py
)

set TEST_EXIT_CODE=%ERRORLEVEL%

REM Summary
echo.
echo ========================================
echo Test Summary
echo ========================================

if %TEST_EXIT_CODE% equ 0 (
    echo [OK] All tests completed successfully!
    echo.
) else (
    echo [ERROR] Tests failed with exit code %TEST_EXIT_CODE%
    echo.
    exit /b %TEST_EXIT_CODE%
)

exit /b 0
