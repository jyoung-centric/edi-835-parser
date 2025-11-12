@echo off
echo Starting EDI 835 FastAPI Mock Service...
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
echo The API will be available at: http://localhost:8000
echo Swagger UI will be at: http://localhost:8000/docs
echo.

REM Go back to fastapi-mock directory and run the app
cd fastapi-mock
python main.py