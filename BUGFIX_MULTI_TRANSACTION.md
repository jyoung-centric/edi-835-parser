# Bug Fix: Multiple Transactions Creating Only 1 Database Record

## Issue
File `SKPA0.13167.20250823.063221913.ERA.835.edi` contains **3 TRN (transactions)** but only **1 record** was created in the database.

## Root Cause
The **parser itself** (`edi_835_parser/transaction_set/transaction_set.py`) had a fundamental design flaw where it only returned the **last transaction** from files containing multiple ST...SE segments:

```python
# OLD CODE (BUGGY in TransactionSet.build())
# When file has multiple ST...SE blocks:
if response.key == 'financial information':
    financial_information = response.value  # ❌ OVERWRITES previous transaction
if response.key == 'trace':
    trace = response.value  # ❌ OVERWRITES previous transaction
# Result: Only last transaction's BPR/TRN kept
```

## Impact
- **Parser** (`TransactionSet.build()`) - ❌ Only returned last transaction from multi-transaction files
- **Database code** (`tests/db_utils.py`) - ✅ Was actually correct (loop handles multiple transactions)

The parser never split files into separate ST...SE segments, causing all but the last transaction to be lost.

## File Details
- **File**: `SKPA0.13167.20250823.063221913.ERA.835.edi`
- **Transactions**: 3
  1. TRN `51007507001764` - $396,017.18 (289 claims)
  2. TRN `51007507001765` - $51.21 (5 claims)
  3. TRN `51007507001766` - $55.00 (4 claims)
- **Total**: $396,123.39, 298 claims

## Fix Applied

### 1. Parser Fix (`edi_835_parser/transaction_set/transaction_set.py`)
Created new method `TransactionSet.build_multiple()` that:

1. **Splits file by ST...SE segments** to extract each transaction separately
2. **Wraps each transaction** with original ISA/GS/GE/IEA envelope
3. **Creates temporary files** for each transaction
4. **Calls `build()` on each** to create separate TransactionSet objects
5. **Returns list of TransactionSet objects** (one per transaction)

```python
# NEW CODE (FIXED)
@classmethod
def build_multiple(cls, file_path: str) -> List['TransactionSet']:
    # Split into ST...SE blocks
    for seg in all_segments:
        if identifier == 'ST':
            in_transaction = True
            current_block = [seg]
        elif identifier == 'SE':
            current_block.append(seg)
            transaction_blocks.append(current_block)  # ✅ Saves each block

    # Build TransactionSet for each block
    for block in transaction_blocks:
        temp_content = ISA + GS + block + GE + IEA
        transaction_set = cls.build(temp_path)
        transaction_sets.append(transaction_set)  # ✅ Multiple objects

    return transaction_sets
```

### 2. Entry Point Fix (`edi_835_parser/__init__.py`)
Updated `parse_to_json()` to:

1. **Use `build_multiple()`** instead of `build()`
2. **Merge all transactions** into single JSON structure
3. **Preserve envelope** (ISA/GS/GE/IEA) from first transaction

```python
# NEW CODE
def _merge_transaction_sets_to_json(transaction_sets):
    merged_json = {
        "interchange": {
            "ISA": first_json["interchange"]["ISA"],
            "GS": first_json["interchange"]["GS"],
            "transactions": [],  # ✅ Collects all transactions
            "GE": ..., "IEA": ...
        }
    }

    for ts in transaction_sets:
        transactions = ts.to_json()["interchange"]["transactions"]
        merged_json["interchange"]["transactions"].extend(transactions)

    return merged_json
```

## Behavior Change
| Scenario | Before (Bug) | After (Fixed) |
|----------|-------------|---------------|
| Parser returns | Last transaction only ❌ | All transactions ✅ |
| File with 1 transaction | 1 record | 1 record |
| File with 3 transactions | 1 record (last only) ❌ | 3 records ✅ |
| Each record stores | Last transaction only | Only its transaction ✅ |
| JSON structure | 1 transaction in array | 3 transactions in array ✅ |

## Testing
To verify the fix works, run:
```bash
# Automated script (recommended)
./run-tests-with-db.sh --keep-db

# Manual verification
docker exec edi-835-test-db psql -U bot -d bot_automation -c \
  "SELECT file_name, check_number, payment_amount FROM bot.payments_835 WHERE file_name LIKE '%SKPA0.13167.20250823%' ORDER BY payment_amount DESC;"

# Expected: 3 rows for SKPA0 file
# 51007507001764 | $396,017.18
# 51007507001765 | $51.21
# 51007507001766 | $55.00
```

## Files Modified
1. **`edi_835_parser/transaction_set/transaction_set.py`**
   - Added `build_multiple()` method to split multi-transaction files
   - Detects ST...SE segments and creates separate TransactionSet objects

2. **`edi_835_parser/__init__.py`**
   - Added `_build_transaction_sets()` (plural) method
   - Added `_merge_transaction_sets_to_json()` to combine results
   - Updated `parse_to_json()` to use new methods
   - Kept `_build_transaction_set()` (singular) for backward compatibility

3. **`run-tests-with-db.sh`**
   - Added virtual environment activation
   - Automated database start, test, and cleanup

## Related Files
- `tests/db_utils.py` - Database insertion (was already correct)
- `test_with_db.py` - Test runner (works correctly with parser fix)

---
**Fixed by**: Claude Code
**Date**: 2026-02-10
