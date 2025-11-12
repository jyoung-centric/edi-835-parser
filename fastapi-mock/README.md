# FastAPI Mock Service for EDI 835 Data

This FastAPI application provides REST endpoints to query EDI 835 payment data stored in TinyDB.

## Features

- Query payments by check number
- Search payments by multiple criteria (payer_id, payee_id, file_name, payment_date)
- List all payments with optional limit
- Get specific payment by database ID
- Health check endpoint

## Installation

The dependencies are already included in the main project's `pyproject.toml`:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `tinydb`: Database (already installed)

## Running the API

### Option 1: Direct Python execution
```bash
cd fastapi-mock
python main.py
```

### Option 2: Using Uvicorn
```bash
cd fastapi-mock
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## API Endpoints

### Root
- `GET /` - API information and available endpoints

### Health Check
- `GET /health` - Health check with database status

### Payment Queries
- `GET /payments/check/{check_number}` - Query by check number
- `GET /payments/search` - Search with query parameters:
  - `payer_id`: Filter by payer ID
  - `payee_id`: Filter by payee ID
  - `file_name`: Filter by file name
  - `payment_date`: Filter by payment date (YYYY-MM-DD)
- `GET /payments` - List all payments (optional `limit` parameter)
- `GET /payments/{payment_id}` - Get specific payment by database ID

## Example Usage

### Query by check number:
```bash
curl "http://localhost:8000/payments/check/CHK001"
```

### Search by payer ID:
```bash
curl "http://localhost:8000/payments/search?payer_id=12345"
```

### List all payments with limit:
```bash
curl "http://localhost:8000/payments?limit=10"
```

## Interactive Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database

The API connects to the TinyDB database file at `../edi_835_data.json` (relative to the parent directory).
Make sure you have some EDI 835 data stored in the database before querying.