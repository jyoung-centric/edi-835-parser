@echo off
echo Loading Mock Data into TinyDB...
echo.

REM Change to the parent directory (project root)
cd /d "%~dp0\.."

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Could not activate virtual environment
    echo Make sure .venv exists in the project root
    pause
    exit /b 1
)

echo Virtual environment activated
echo.

REM Go back to fastapi-mock directory and run the data loader
cd fastapi-mock
python load_mock_data.py

echo.
echo Press any key to continue...
pause