# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An EDI 835 Healthcare Payment Parser with enhanced JSON output capabilities and database integration. Parses EDI 835 Health Care Claim Payment and Remittance Advice files into structured Python objects or JSON format. Internal use only - not open source.

**Based on**: Fork of [edi-835-parser](https://github.com/keironstoddart/edi-835-parser) by Keiron Stoddart with significant enhancements for production healthcare payment processing.

**Requirements**: Python 3.9+

## Development Commands

### Testing
```bash
# Run pytest test suite
python -m pytest

```

### Database Schema Management (PostgreSQL)
```bash
# Set environment variables for target database
export DB_URL=postgresql://botdb.prxdev.com:5432/bot_automation?currentSchema=bot
export DB_USER=bot
export DB_PASSWORD=<PASSWORD>

# Run Flyway migrations using Docker Compose
cd schema-bot-automation-main
docker compose run --rm flyway migrate

# Or run full deployment sequence (repair, migrate, validate)
docker compose up
```

### Installation
```bash
# Using Poetry (preferred)
poetry install

# Using pip
pip install -e .
```

## Architecture

### Dual Parsing Modes

1. **Object-Based Parsing** (`edi_835_parser.parse()`)
   - Returns `TransactionSets` containing structured Python objects
   - Useful for programmatic access and DataFrame conversion
   - Objects: `TransactionSet`, `ClaimLoop`, `ServiceLoop`, `OrganizationLoop`

2. **JSON Parsing** (`edi_835_parser.parse_to_json()`)
   - Direct conversion to JSON structure (recommended for integration)
   - Uses object-based parsing internally, then converts via mixins
   - Proper DTM date placement at claim and service levels

### Core Structure

```
edi_835_parser/
├── elements/          # Primitives: dates, amounts, codes, qualifiers
├── segments/          # EDI segments: CLP, SVC, DTM, BPR, TRN, etc.
├── loops/             # Higher-level structures
│   ├── claim.py       # CLP_loop (claims)
│   ├── service.py     # SVC_loop (services within claims)
│   └── organization.py # N1_loop (payer/payee)
└── transaction_set/   # Top-level transaction processing

core/
├── parser_extension.py    # JSON conversion mixins (ClaimLoopJsonMixin, ServiceLoopJsonMixin, etc.)
└── parser_monkeypatch.py  # Applies mixins to parser classes

schema-bot-automation-main/    # PostgreSQL schema (source of truth)
├── migrations/                # Flyway migration scripts
│   ├── V1.0.1__create_test_table.sql
│   └── V1.0.2__create edi bot tables.sql
├── compose.yaml               # Docker Compose for Flyway deployment
└── README.md                  # Deployment documentation
```

### Database Schema Architecture

**Schema Management** (`schema-bot-automation-main/`):
- PostgreSQL schema managed via Flyway migrations
- Deployed using Docker Compose + Jenkins automation
- Migration naming: `V{major}.{minor}.{patch}__{description}.sql`

**Database Tables** (defined in `V1.0.2__create edi bot tables.sql`):

1. **Simple Storage** (for complete EDI data):
   - `payments_835`: Main table with complete JSON and summary fields
     - `file_id`, `file_name`, `receive_date_time`
     - `check_number`, `payment_date`, `payment_amount`
     - `payer_id`, `payee_id`
     - `json_transaction` (JSONB - complete parsed data)
     - `raw_edi` (TEXT - original EDI content)

2. **Normalized Storage** (for structured queries):
   - `raw_835_files`: Raw file metadata with S3 archive keys
   - `edi_transactions`: Transaction level (BPR/TRN) with trace numbers
   - `payers` / `payees`: Organization entities with identifiers
   - `claims`: Claim level (CLP) with patient control numbers, ICN, amounts
   - `service_lines`: Service level (SVC) with HCPCS codes, modifiers, units
   - `nm1_entities`: Name entities (patient, provider, etc.)
   - `cas_adjustments`: Claim/service adjustments with reason codes
   - `plb_adjustments`: Provider level balance adjustments

### Extension System

**JSON Conversion Mixins** (`core/parser_extension.py`):
- `ClaimLoopJsonMixin`: Converts ClaimLoop → JSON with CLP, DTM, NM1, SVC_loop
- `ServiceLoopJsonMixin`: Converts ServiceLoop → JSON with SVC, DTM, CAS
- Applied via monkey patching in `core/parser_monkeypatch.py`
- All data comes from parsed objects (no re-parsing or hardcoded values)

### Key Enhancement: DTM Date Handling

**Fixed Implementation**:
- Claim-level dates: `CLP_loop[].DTM[]` (from `claims[].dates[]`)
- Service-level dates: `SVC_loop[].DTM[]` (from `services[].dates[]`)
- Uses actual parsed date objects with proper formatting
- No hardcoded placeholder dates

### Preprocessing

**Special Character Handling** (`edi_835_parser.preprocess_edi_content()`):
- Automatically replaces non-standard separators:
  - `\x1d` → `*` (element separator)
  - `\x1e` → `~` (component separator)
  - `\x1f` → `:` (segment terminator)
  - `\n` → removed (line breaks)
- Creates temporary `.processed.tmp` files
- Enabled by default in `parse()` and `parse_to_json()`

## Usage Patterns

### Basic Parsing
```python
import edi_835_parser

# Object-based
transaction_sets = edi_835_parser.parse('file.txt')
df = transaction_sets.to_dataframe()

# JSON (recommended)
json_data = edi_835_parser.parse_to_json('file.txt')
transactions = json_data['interchange']['transactions']
claims = transactions[0]['CLP_loop']
```

### Database Storage
```python
import edi_835_parser

# Parse EDI file to JSON
json_data = edi_835_parser.parse_to_json('file.txt')

# Extract summary fields for payments_835 table
transactions = json_data['interchange']['transactions']
bpr = transactions[0]['BPR']
trn = transactions[0]['TRN']

# Prepare data for database insert
payment_data = {
    'file_name': 'file.txt',
    'json_transaction': json_data,
    'raw_edi': open('file.txt').read(),
    'check_number': trn.get('reference_identification'),
    'payment_date': bpr.get('check_issue_or_eft_effective_date'),
    'payment_amount': bpr.get('monetary_amount'),
    'payer_id': trn.get('originating_company_identifier')
}

# Insert into PostgreSQL payments_835 table
# (Connection and insert logic depends on your database client)
```

## Test Files

Located in `tests/test_edi_835_files/`:
- Sample EDI 835 files from various payers (Blue Cross NC, UHC, etc.)
- Large files with 700+ claims for stress testing
- Files with special characters requiring preprocessing

## Key Files

- `edi_835_parser/__init__.py`: Main entry points (`parse`, `parse_to_json`)
- `edi_835_parser/transaction_set/transaction_set.py`: Core TransactionSet class with `to_json()` method
- `core/parser_extension.py`: JSON conversion mixins
- `schema-bot-automation-main/migrations/V1.0.2__create edi bot tables.sql`: PostgreSQL schema definition
- `schema-bot-automation-main/compose.yaml`: Flyway deployment configuration

## Data Flow

### EDI Processing Flow
1. **Parse**: EDI file → `TransactionSet` object (via `TransactionSet.build()`)
2. **Convert**: `TransactionSet.to_json()` → applies mixins → JSON structure
3. **Store**: JSON → PostgreSQL `payments_835` table (and optionally normalized tables)
4. **Query**: Applications/APIs → PostgreSQL queries → Structured data

### Schema Deployment Pipeline
1. **Migration Script**: Create `V{version}__{description}.sql` in `migrations/`
2. **Version Control**: Commit to repository
3. **Jenkins**: Automatically triggers on merge to main branch
4. **Docker Compose**: Runs Flyway container with `repair`, `migrate`, `validate` commands
5. **Database**: Schema changes applied to PostgreSQL bot_automation database
6. **History**: Flyway tracks applied migrations in `flyway_schema_history` table

## Database Schema Important Notes

### Flyway Migration Rules
- Migration files MUST follow naming: `V{major}.{minor}.{patch}__{description}.sql`
- Version must have uppercase `V` prefix
- Double underscore `__` separates version from description
- CANNOT have duplicate versions with different descriptions
- Migrations are immutable once applied - create new version to modify
- Archived migrations in `archive/` folder are not executed

### Database Roles
- `bot`: Database owner with CREATEDB and CREATEROLE privileges
- `botuser`: Application user with SELECT, INSERT, UPDATE, DELETE on tables
- `postgres`: Superuser for creating extensions and initial setup

### Schema Search Path
- Default schema: `bot` (set via `ALTER ROLE SET search_path TO bot`)
- All tables created in `bot` schema
- Extensions installed in `pg_catalog` schema

## General Notes

- Internal tool - not for public distribution
- Focus on healthcare payment processing accuracy
- Handles real-world EDI variations and edge cases
- Performance: ~0.35s for 11 files, handles 700+ claims/file efficiently
- Database schema is source of truth in `schema-bot-automation-main/`
- PostgreSQL database managed via Flyway migrations
