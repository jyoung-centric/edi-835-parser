# Windows Test Runner - Quick Start Guide

This guide shows you how to run EDI 835 Parser tests on Windows using PostgreSQL.

## Quick Start (3 Steps)

### 1. Configure Database Connection

Add the following parameters to your `.env` file:

```env
# PostgreSQL Test Database Configuration
TEST_DB_HOST=your-db-hostname
TEST_DB_PORT=5432
TEST_DB_NAME=bot_automation
TEST_DB_USER=bot
TEST_DB_PASSWORD=your-password-here
TEST_DB_SCHEMA=bot
```

> **Tip**: See [.env.example](.env.example) for reference

### 2. Ensure Virtual Environment is Set Up

```powershell
# PowerShell - Create venv if needed
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```cmd
:: Command Prompt
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 3. Run Tests

**PowerShell (Recommended)**
```powershell
.\run-tests-with-db.ps1
```

**Command Prompt**
```cmd
run-tests-with-db.bat
```

**Git Bash / WSL**
```bash
./run-tests-with-db.sh  # Original script for local Docker
```

## Command Options

### PowerShell Script

```powershell
# Basic run (cleans and seeds data)
.\run-tests-with-db.ps1

# Keep data between test runs
.\run-tests-with-db.ps1 -KeepData
```

### Batch Script

```cmd
rem Basic run
run-tests-with-db.bat

rem Keep data between test runs
run-tests-with-db.bat --keep-data
```

## File Overview

| File | Purpose |
|------|---------|
| `run-tests-with-db.ps1` | **PowerShell script** for Windows |
| `run-tests-with-db.bat` | **Batch script** for Windows (cmd.exe compatible) |
| `run-tests-with-db.sh` | **Bash script** for Linux/macOS with Docker |
| `.env.example` | Template for database configuration |
| `.env` | Your actual database credentials (not in git) |

## Comparison: Local Docker vs Remote PostgreSQL

### Original Script (`run-tests-with-db.sh`)
- ✅ Runs on Linux/macOS/WSL
- ✅ Uses local Docker PostgreSQL
- ✅ Manages database lifecycle (start/stop)
- ❌ Requires Docker Desktop
- ❌ Not native Windows

### New Scripts (`run-tests-with-db.ps1` / `.bat`)
- ✅ Native Windows support
- ✅ Works with existing PostgreSQL instance
- ✅ No Docker required
- ✅ Can use shared team database
- ❌ Requires existing database setup

## Troubleshooting

### "Cannot connect to database"

1. **Verify database is running**
   - Check that PostgreSQL service is active
   - Confirm host and port are correct

2. **Test connectivity**
   ```powershell
   Test-NetConnection -ComputerName your-db-host -Port 5432
   ```

3. **Check credentials**
   - Verify username and password in `.env`
   - Ensure no extra spaces in `.env` file

### "Schema 'bot' does not exist"

Run the initialization SQL:
```powershell
# Using psql (if installed)
psql -h your-db-host -U bot -d bot_automation -f db/init/01-init-schema.sql

# Or use Python
python -c "
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv('TEST_DB_HOST'),
    port=os.getenv('TEST_DB_PORT'),
    database=os.getenv('TEST_DB_NAME'),
    user=os.getenv('TEST_DB_USER'),
    password=os.getenv('TEST_DB_PASSWORD')
)
with conn.cursor() as cur:
    cur.execute('CREATE SCHEMA IF NOT EXISTS bot')
conn.commit()
conn.close()
"
```

### PowerShell Execution Policy

If you see "running scripts is disabled", run:
```powershell
# As Administrator or Current User
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Module 'psycopg2' not found

Install the required package:
```powershell
pip install psycopg2-binary
```

## Security Notes

- ✅ `.env` is in `.gitignore` (never commit credentials)
- ✅ Use strong passwords
- ✅ Restrict database access to necessary hosts only
- ✅ Use SSL/TLS for database connections when possible

## Example Run Output

```
🚀 EDI 835 Parser - Test Runner
==========================================

✅ Found .env configuration file
🔹 Loading database configuration...
   Set TEST_DB_HOST
   Set TEST_DB_PORT
   Set TEST_DB_NAME
   Set TEST_DB_USER
   Set TEST_DB_PASSWORD
   Set TEST_DB_SCHEMA
✅ Configuration loaded
🔹 Activating Python virtual environment...
✅ Virtual environment activated (.venv)

🧪 Running tests with database
==========================================

Starting database seeding...
[Test output...]
✅ All tests passed!

Test Summary
==========================================
✅ All tests completed successfully!
```
