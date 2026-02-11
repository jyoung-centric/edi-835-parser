# Middle Name/Initial Parsing Fix - Summary

## Issue
The EDI 835 parser was not capturing middle names, name prefixes, or name suffixes from NM1 segments.

Example: `PELIKAN, LAUREN J` → Middle initial "J" was being dropped

## Root Cause
Two defects in the parsing logic:

1. **Entity Parser** (`edi_835_parser/segments/entity.py`):
   - Only parsed segment positions [3, 4, 8, 9]
   - Skipped positions [5, 6, 7] which contain middle_name, prefix, suffix

2. **JSON Conversion** (`core/parser_extension.py`):
   - Hardcoded empty strings for middle_name, name_prefix, name_suffix
   - Did not use parsed values from Entity objects

## Changes Made

### 1. Fixed Entity Parser (entity.py)
**Added parsing for NM1 segment positions:**
- `segment[5]` → `self.middle_name`
- `segment[6]` → `self.name_prefix`
- `segment[7]` → `self.name_suffix`

**Updated `name` property to include middle name:**
```python
@property
def name(self) -> str:
    name_parts = [self.first_name, self.middle_name, self.last_name]
    full_name = ' '.join(part for part in name_parts if part)
    return full_name.title()
```

### 2. Fixed JSON Conversion (parser_extension.py)
**Changed from hardcoded empty strings to parsed values:**
```python
"middle_name": self.patient.middle_name or "",
"name_prefix": self.patient.name_prefix or "",
"name_suffix": self.patient.name_suffix or "",
```

### 3. Database Migration (V1.0.3)
**Created:** `schema-bot-automation-main/migrations/V1.0.3__add_name_prefix_suffix_to_nm1_entities.sql`

**Changes:**
- Added `name_prefix TEXT` column to `bot.nm1_entities`
- Added `name_suffix TEXT` column to `bot.nm1_entities`
- Note: `middle_name` column already existed

## Verification Tests

### Test 1: Middle Initial
**Input:** `NM1*QC*1*PELIKAN*LAUREN*J***MI*2094109622~`

**Output:**
```
Last Name: 'PELIKAN'
First Name: 'LAUREN'
Middle Name: 'J' ✓ CAPTURED!
Full Name: LAUREN J PELIKAN
```

### Test 2: Complete Name with Prefix/Suffix
**Input:** `NM1*QC*1*SMITH*JOHN*M*DR*JR*MI*1234567890~`

**Output:**
```
Prefix: 'DR'
First: 'JOHN'
Middle: 'M'
Last: 'SMITH'
Suffix: 'JR'
```

### Test 3: Entity.name Property
**Result:** `'John M Smith'` (correctly includes middle name)

## Database Deployment

### Prerequisites
```bash
export DB_URL=postgresql://botdb.prxdev.com:5432/bot_automation?currentSchema=bot
export DB_USER=bot
export DB_PASSWORD=<PASSWORD>
```

### Deploy Migration
```bash
cd schema-bot-automation-main
docker compose run --rm flyway migrate
```

### Verify Migration
```bash
# Check migration was applied
docker compose run --rm flyway info

# Expected output should show:
# V1.0.3 | add_name_prefix_suffix_to_nm1_entities | Success
```

### Validate Schema
```bash
# Connect to PostgreSQL and verify columns exist
psql $DB_URL -U $DB_USER -c "\d bot.nm1_entities"

# Should show:
# - first_name      | text
# - middle_name     | text
# - last_name       | text
# - name_prefix     | text  (NEW)
# - name_suffix     | text  (NEW)
```

## Files Modified

1. ✓ `/home/jeremy/centric/edi-835-parser/edi_835_parser/segments/entity.py`
   - Added middle_name, name_prefix, name_suffix parsing
   - Updated name property

2. ✓ `/home/jeremy/centric/edi-835-parser/core/parser_extension.py`
   - Changed hardcoded empty strings to use parsed values

3. ✓ `/home/jeremy/centric/edi-835-parser/schema-bot-automation-main/migrations/V1.0.3__add_name_prefix_suffix_to_nm1_entities.sql`
   - New migration to add name_prefix and name_suffix columns

## Impact

### JSON Output
All parsed JSON will now include:
```json
{
  "NM1": [{
    "first_name": "LAUREN",
    "middle_name": "J",
    "last_name": "PELIKAN",
    "name_prefix": "",
    "name_suffix": ""
  }]
}
```

### Database Storage
The `bot.nm1_entities` table can now store complete name information:
- Enables queries like: `WHERE middle_name = 'J'`
- Supports filtering by prefix (Dr., Mr., Ms.)
- Supports filtering by suffix (Jr., Sr., III)

### Backward Compatibility
✓ **Fully backward compatible**
- Existing records: NULL values for new columns
- Empty fields: Empty strings (not NULL)
- No data loss or breaking changes

## Next Steps

1. **Deploy Migration:** Run Flyway migration V1.0.3 to production database
2. **Monitor:** Check that new EDI files are populating middle_name/prefix/suffix
3. **Reprocess (Optional):** If needed, reprocess historical EDI files to populate middle names

## Testing

Run the comprehensive test suite:
```bash
# Full test suite
python -m pytest

# Comprehensive test runner
python ShubhamTest.py
```

All tests should pass with middle name fields now properly populated.
