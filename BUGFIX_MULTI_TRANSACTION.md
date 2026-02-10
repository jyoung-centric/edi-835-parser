# Bug Fix: Multiple Transactions Creating Only 1 Database Record

## Issue
File `SKPA0.13167.20250823.063221913.ERA.835.edi` contains **3 TRN (transactions)** but only **1 record** was created in the database.

## Root Cause
The test utility `tests/db_utils.py:insert_payment_835()` had a bug where it only processed the **first transaction** from files containing multiple transactions:

```python
# OLD CODE (BUGGY)
first_transaction = transactions[0]  # ❌ Only used first transaction
# Then inserted only ONE record
```

## Impact
- **Production code** (`db/seed.py`) - ✅ Correctly handles multiple transactions
- **Test code** (`tests/db_utils.py`) - ❌ Only inserted first transaction

This caused discrepancies between test results and production behavior.

## File Details
- **File**: `SKPA0.13167.20250823.063221913.ERA.835.edi`
- **Transactions**: 3
  1. TRN `51007507001764` - $396,017.18 (289 claims)
  2. TRN `51007507001765` - $51.21 (5 claims)
  3. TRN `51007507001766` - $55.00 (4 claims)
- **Total**: $396,123.39, 298 claims

## Fix Applied
Updated `tests/db_utils.py:insert_payment_835()` to:

1. **Loop through ALL transactions** instead of just the first one
2. **Create one `payments_835` record per transaction**
3. **Generate unique `file_id` per transaction** using uuid5 for deterministic IDs
4. **Store single-transaction JSON** in each record (cleaner than storing full file)

```python
# NEW CODE (FIXED)
for txn_index, transaction in enumerate(transactions):
    # Generate unique file_id per transaction
    if txn_index == 0:
        file_id = base_file_id
    else:
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        file_id = uuid.uuid5(namespace, f"{file_name}::txn_{txn_index}")

    # Create transaction-specific JSON (only this transaction)
    single_transaction_json = {
        "interchange": {
            "ISA": json_data.get("interchange", {}).get("ISA"),
            "GS": json_data.get("interchange", {}).get("GS"),
            "transactions": [transaction],  # ✅ Only this transaction
            "GE": json_data.get("interchange", {}).get("GE"),
            "IEA": json_data.get("interchange", {}).get("IEA")
        }
    }

    # Insert record
    self.cursor.execute(insert_query, (..., Json(single_transaction_json), ...))
```

## Behavior Change
| Scenario | Before (Bug) | After (Fixed) |
|----------|-------------|---------------|
| File with 1 transaction | 1 record | 1 record |
| File with 3 transactions | 1 record ❌ | 3 records ✅ |
| Each record stores | All transactions | Only its transaction ✅ |

## Testing
To verify the fix works, run:
```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Run test with database seeding
source .venv/bin/activate
python test_with_db.py

# Verify 3 records created for SKPA0 file
```

## Files Modified
- `tests/db_utils.py` - Fixed `insert_payment_835()` method

## Related Files
- `db/seed.py` - Production code (already correct)
- `main.py` - Uses production seed code
- `test_with_db.py` - Uses test utility (now fixed)

---
**Fixed by**: Claude Code
**Date**: 2026-02-10
