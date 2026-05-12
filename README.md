# EDI 835 Parser

### edi-835-parser: Advanced EDI 835 Healthcare Payment Parser

This package provides a comprehensive Python interface for parsing EDI 835 Health Care Claim Payment and Remittance Advice files with enhanced JSON output capabilities and PostgreSQL database integration.

*This package is distributed for internal use only. It is not available as open source or for public download.*

## Key Features

- **Dual Parsing Modes**: Object-based parsing and direct JSON conversion
- **Comprehensive Data Extraction**: Claims, services, dates, amounts, and references
- **NM1 Entity Parsing**: Full name support including middle name, prefix, and suffix
- **CAS Adjustment Handling**: Claim and service-level adjustments with group/reason codes
- **DTM Date Handling**: Proper extraction and placement of dates at claim and service levels
- **Multi-Transaction Support**: Single EDI files containing multiple ST...SE blocks
- **Preprocessing Support**: Automatic handling of files with special character separators
- **PostgreSQL Integration**: Store parsed data directly into the production database schema
- **Batch Processing**: Process multiple files with automated reporting

## Installation

Python 3.9 or higher is required.

```bash
# Using Poetry (preferred)
poetry install

# Using pip
pip install -e .
```

## Usage

### Object-Based Parsing

Parse an EDI 835 file and work with structured Python objects:

```python
import edi_835_parser

# Parse a single file
transaction_sets = edi_835_parser.parse('path/to/file.txt')

# Parse a directory of files
transaction_sets = edi_835_parser.parse('path/to/directory/')

# Convert to Pandas DataFrame
df = transaction_sets.to_dataframe()
df.to_csv('output.csv')
```

### JSON Parsing (Recommended)

Parse directly to a JSON-compatible dictionary for easier integration:

```python
import edi_835_parser

json_data = edi_835_parser.parse_to_json('tests/test_edi_835_files/blue_cross_nc_sample.txt')

# Navigate the structure
transactions = json_data['interchange']['transactions']
claims = transactions[0]['CLP_loop']
services = claims[0]['SVC_loop']

# DTM dates at the right level
claim_dates = claims[0]['DTM']    # Claim-level dates
service_dates = services[0]['DTM']  # Service-level dates

# NM1 with full name fields
patient = claims[0]['NM1'][0]
print(patient['last_name'], patient['first_name'], patient.get('middle_name'))
print(patient.get('name_prefix'), patient.get('name_suffix'))
```

### Database Storage

There are two ways to store parsed data in PostgreSQL.

#### Simple — `payments_835` only (`db/manager.py`)

Inserts one row per transaction into `payments_835` with the full JSON blob and raw EDI. Use this when you need basic storage and query via PostgreSQL JSON operators.

```python
import edi_835_parser
from db import get_database_manager

json_data = edi_835_parser.parse_to_json('path/to/file.txt')
raw_edi = open('path/to/file.txt').read()

db = get_database_manager()
if db.connect():
    db.insert_payment_835(
        file_name='file.txt',
        json_data=json_data,
        raw_edi=raw_edi
    )
    db.disconnect()
```

`get_database_manager()` reads from environment variables:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | Database hostname |
| `DB_PORT` | `5433` | Database port |
| `DB_NAME` | `bot_automation` | Database name |
| `DB_USER` | `bot` | Database user |
| `DB_PASSWORD` | `bot_test_password` | Database password |
| `DB_SCHEMA` | `bot` | Schema name |

#### Normalized — all tables (`db/seed.py`)

Inserts into all normalized tables (payments_835, raw_835_files, edi_transactions, payers, payees, claims, service_lines, nm1_entities, cas_adjustments, plb_adjustments). Use this when you need structured SQL queries against individual claims, service lines, or adjustments.

```python
import edi_835_parser
from db.connection import load_config, get_connection
from db.models import generate_file_id
from db.seed import seed_file

json_data = edi_835_parser.parse_to_json('path/to/file.txt')
raw_edi = open('path/to/file.txt').read()

config = load_config()  # reads DB_* vars from .env
conn = get_connection(config)

file_id = generate_file_id('file.txt')  # deterministic UUID for idempotency
stats = seed_file(conn, file_id, 'file.txt', json_data, raw_edi)

print(stats)
# {'transactions': 1, 'claims': 42, 'service_lines': 87, 'payers': 1, ...}

conn.close()
```

Copy `.env.example` to `.env` and fill in the values for your environment. Both storage approaches read from the same `DB_*` variables.

## Testing

### Unit Tests

```bash
python -m pytest
```

### Tests with Database

#### Linux / macOS

```bash
# Start a Docker PostgreSQL container, run tests, then tear down
./run-tests-with-db.sh
```

#### Windows (PowerShell)

```powershell
.\run-tests-with-db.ps1
```

#### Windows (Command Prompt)

```cmd
run-tests-with-db.bat
```

Configure database connection in `.env`:

```env
DB_HOST=your-db-hostname
DB_PORT=5432
DB_NAME=bot_automation
DB_USER=bot
DB_PASSWORD=your-password
DB_SCHEMA=bot
```

See [WINDOWS_QUICK_START.md](WINDOWS_QUICK_START.md) for detailed Windows setup.

### Test Files

EDI 835 sample files are in `tests/test_edi_835_files/`:

| File | Description |
|---|---|
| `blue_cross_nc_sample.txt` | Blue Cross NC — 1 claim |
| `emedny_sample.txt` | eMedNY — 3 claims |
| `united_healthcare_legacy_sample.txt` | UHC legacy format — 2 claims |
| `PT13882.0021984 1.DT20240821` | Large file — 778+ claims |
| `SB865.13167.20250622.061330708.ERA.835NP.edi` | Complex format — 707+ claims |
| `SKPA0.13167.20250823.063221913.ERA.835.edi` | Multi-transaction format |
| Additional files | Various payer formats for edge case testing |

## JSON Output Format

```json
{
  "interchange": {
    "ISA": {},
    "GS": {},
    "transactions": [{
      "ST": {},
      "BPR": { "monetary_amount": "1000.00", "check_issue_or_eft_effective_date": "20240101" },
      "TRN": { "reference_identification": "CHECK12345" },
      "DTM": [],
      "N1_loop": [],
      "CLP_loop": [{
        "CLP": { "patient_control_number": "...", "claim_status_code": "1" },
        "DTM": [{ "date_time_qualifier": "232", "date": "20240101" }],
        "NM1": [{
          "last_name": "Smith",
          "first_name": "John",
          "middle_name": "A",
          "name_prefix": "Dr",
          "name_suffix": "Jr"
        }],
        "CAS": [],
        "SVC_loop": [{
          "SVC": { "procedure_code": "99213", "line_item_charge_amount": "150.00" },
          "DTM": [{ "date_time_qualifier": "472", "date": "20240101" }],
          "CAS": []
        }]
      }]
    }],
    "GE": {},
    "IEA": {}
  }
}
```

## Project Structure

```
edi-835-parser/
├── edi_835_parser/               # Core parser package
│   ├── __init__.py               # API entry points (parse, parse_to_json)
│   ├── elements/                 # Primitive types (codes, amounts, dates, qualifiers)
│   ├── segments/                 # EDI segment parsers (CLP, SVC, DTM, NM1, BPR, TRN, etc.)
│   ├── loops/                    # Loop structures (claim, service, organization)
│   └── transaction_set/          # Core transaction processing
├── core/                         # JSON extension system
│   ├── parser_extension.py       # JSON conversion mixins
│   └── parser_monkeypatch.py     # Applies mixins to parser classes
├── db/                           # PostgreSQL database integration
│   ├── __init__.py               # Package exports
│   ├── connection.py             # Production connection factory (DB_* env vars)
│   ├── manager.py                # Simple storage: insert/query payments_835 only
│   ├── models.py                 # Row builders for all normalized tables
│   └── seed.py                   # Normalized insert across all tables
├── schema-bot-automation-main/   # PostgreSQL schema (source of truth)
│   ├── migrations/               # Flyway migration scripts
│   │   ├── V1.0.1__create_test_table.sql
│   │   ├── V1.0.2__create edi bot tables.sql
│   │   └── V1.0.3__align_edi_835_parser_schema.sql
│   └── compose.yaml              # Docker Compose for Flyway deployment
├── sql/                          # SQL utility queries
├── tests/
│   ├── conftest.py               # Pytest fixtures
│   ├── test_edi_835_parser.py    # Unit tests
│   ├── test_all_files.py         # Integration tests
│   ├── test_edi_835_files/       # Sample EDI files
│   └── output/                   # Generated JSON outputs (git-ignored)
├── test_with_db.py               # Database integration test runner
├── docker-compose.test.yml       # Docker PostgreSQL for local testing
├── run-tests-with-db.sh          # Linux/macOS test runner
├── run-tests-with-db.ps1         # Windows PowerShell test runner
├── run-tests-with-db.bat         # Windows batch test runner
├── .env.example                  # Environment variable template
└── pyproject.toml                # Poetry project configuration
```

## Database Schema

The PostgreSQL schema is managed via Flyway migrations in `schema-bot-automation-main/`. Deploy using Docker Compose:

```bash
cd schema-bot-automation-main
docker compose run --rm flyway migrate
```

### Key Tables

**Simple storage** (`db/manager.py` — `insert_payment_835`):

| Table | Purpose |
|---|---|
| `payments_835` | One record per transaction — full JSONB + raw EDI + summary fields |

**Normalized storage** (`db/seed.py` — `seed_file`):

| Table | Purpose |
|---|---|
| `payments_835` | Same as above — inserted first as the root record |
| `raw_835_files` | File metadata and S3 archive key; FK to `payments_835.file_id` |
| `edi_transactions` | BPR/TRN data: trace number, payment method, amounts, dates |
| `payers` / `payees` | Organization name and ID from N1_loop (PR / PE) |
| `claims` | CLP data: patient control number, ICN, status, charge and net amounts |
| `service_lines` | SVC data: HCPCS code, modifiers, charge, payment, units |
| `nm1_entities` | Patient/provider names, identifiers, and source NM1 JSON |
| `cas_adjustments` | One row per adjustment reason code within each CAS segment |
| `plb_adjustments` | Provider-level balance adjustments (PLB segment) |

### Migration Rules

- Files must be named `V{major}.{minor}.{patch}__{description}.sql`
- Uppercase `V` prefix and double underscore separator are required
- Applied migrations are immutable — create a new version to modify schema

## Architecture

### Dual Parsing Modes

```
EDI File
  ├── parse()         → TransactionSets → to_dataframe() → CSV / Pandas
  └── parse_to_json() → Dict            → PostgreSQL / API / JSON file
```

### JSON Extension System

JSON conversion is handled by mixins applied via monkey patching:

```
ClaimLoop / ServiceLoop / OrganizationLoop
       ↓  (parser_extension.py)
   Mixins add to_dict() methods
       ↓  (parser_monkeypatch.py)
   Applied at import time
```

All values come from parsed EDI objects — no re-parsing or hardcoded data.

### Multi-Transaction File Handling

Some EDI files contain multiple ST...SE blocks. `TransactionSet.build_multiple()` splits them into individual transaction sets and `parse_to_json()` merges them under a single interchange envelope.

### Preprocessing

Files using non-standard separators are detected automatically and preprocessed before parsing:

| Character | Replacement |
|---|---|
| `\x1d` (Group Separator) | `*` (element separator) |
| `\x1e` (Record Separator) | `~` (component separator) |
| `\x1f` (Unit Separator) | `:` (segment terminator) |
| `\n` (newline) | removed |

## Performance

- ~0.35 seconds to process 11 files
- 778 claims parsed in 0.06 seconds
- Tested against 2,600+ claims and 3,800+ service lines per run

## Attribution

Based on the original open-source [edi-835-parser](https://github.com/keironstoddart/edi-835-parser) by Keiron Stoddart. This version is maintained as a closed-source internal tool with significant enhancements for production healthcare payment processing.
