# EDI 835 Parser - Test Runner for Windows
# Usage: .\run-tests-with-db.ps1 [-KeepData]
# 
# Prerequisites:
# - PostgreSQL connection parameters in .env file
# - Python virtual environment set up

[CmdletBinding()]
param(
    [switch]$KeepData
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Main script starts here
Write-Host ""
Write-Host "🚀 EDI 835 Parser - Test Runner" -ForegroundColor Cyan
Write-Host ("=" * 40) -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "ℹ️  Please create .env with database connection parameters." -ForegroundColor Yellow
    Write-Host "ℹ️  Required variables: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found .env configuration file" -ForegroundColor Green

# Load environment variables from .env
Write-Host ""
Write-Host "🔹 Loading database configuration..." -ForegroundColor White
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        Write-Host "   Set $key" -ForegroundColor Gray
    }
}

Write-Host "✅ Configuration loaded" -ForegroundColor Green

# Activate virtual environment
Write-Host ""
Write-Host "🔹 Activating Python virtual environment..." -ForegroundColor White
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
    Write-Host "✅ Virtual environment activated (.venv)" -ForegroundColor Green
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
    Write-Host "✅ Virtual environment activated (venv)" -ForegroundColor Green
} else {
    Write-Host "ℹ️  No virtual environment found (.venv or venv)" -ForegroundColor Yellow
    Write-Host "ℹ️  Proceeding with system Python..." -ForegroundColor Yellow
}

# Run tests
Write-Host ""
Write-Host "🧪 Running tests with database" -ForegroundColor Cyan
Write-Host ("=" * 40) -ForegroundColor Cyan
Write-Host ""

$testArgs = @()
if ($KeepData) {
    $testArgs += "--keep-data"
    Write-Host "ℹ️  Running with --keep-data flag (data will not be cleared)" -ForegroundColor Yellow
}

$testExitCode = 0
try {
    if ($testArgs.Count -gt 0) {
        python test_with_db.py $testArgs
    } else {
        python test_with_db.py
    }
    $testExitCode = $LASTEXITCODE
} catch {
    $testExitCode = 1
    Write-Host "❌ Test execution failed: $_" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host ("=" * 40) -ForegroundColor Cyan
Write-Host ""

if ($testExitCode -eq 0) {
    Write-Host "✅ All tests completed successfully!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "❌ Tests failed with exit code $testExitCode" -ForegroundColor Red
    Write-Host ""
    exit $testExitCode
}

exit 0
