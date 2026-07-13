#!/usr/bin/env python3
"""
EDI 835 Parser — Main entry point

Usage:
    # Parse a single file (prints summary)
    python main.py --file path/to/file.txt

    # Parse all EDI files in a directory
    python main.py --dir path/to/dir/

    # Parse and seed all normalized database tables
    python main.py --file path/to/file.txt --seed-db
    python main.py --file path/to/file.txt --seed-db --location ATL --source-system claims-api --metadata '{"batch_id":"123"}'
    python main.py --dir path/to/dir/ --seed-db

Recognized file extensions: .txt, .835, .edi, .DAT
DB credentials are read from .env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA).
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import edi_835_parser
from db.models import generate_file_id

logger = logging.getLogger(__name__)

DEFAULT_EXTENSION_PATTERN = r'\.(DAT|txt|edi|PCT|835|[a-zA-Z]{1,2}\d{8}|\d{6}|\d{8})$|^[^.]+$'


def extensions_to_regex(ext_input: str) -> str:
    """Convert user-friendly extension input to a regex pattern.

    Accepts:
      - A raw regex (contains regex metacharacters) — merged with default pattern
      - Space-separated extensions:  "DAT txt edi"
      - Comma-separated extensions:  "DAT,txt,edi" or ".DAT,.txt,.edi"
      - A single extension:          "835" or ".835"

    The resulting pattern always includes the default extensions so that
    passing a custom value never drops files that would otherwise be matched
    by the default configuration.

    Returns a combined regex pattern.
    """
    # If caller passed the default unchanged, return it directly.
    if ext_input == DEFAULT_EXTENSION_PATTERN:
        return ext_input

    # Detect whether the input is already a regex (contains metacharacters).
    regex_metacharacters = set(r'\^$*+?{}[]|()')
    has_meta = any(c in regex_metacharacters for c in ext_input)

    if has_meta:
        custom_pattern = ext_input
    else:
        # Split on commas and/or whitespace to get plain extension tokens.
        parts = re.split(r'[,\s]+', ext_input.strip())
        parts = [p.strip().lstrip('.') for p in parts if p.strip()]

        if not parts:
            return DEFAULT_EXTENSION_PATTERN

        escaped = [re.escape(p) for p in parts]
        custom_pattern = r'\.(' + '|'.join(escaped) + r')$'

    # Merge custom pattern with the default so default-extension files are
    # never inadvertently skipped when a custom value is provided.
    return f'(?:{custom_pattern})|(?:{DEFAULT_EXTENSION_PATTERN})'


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_edi_files(directory: str, extension_pattern: str = DEFAULT_EXTENSION_PATTERN) -> Tuple[List[str], List[str]]:
    """Return sorted list of EDI file paths found in directory using regex pattern.
    
    Returns:
        Tuple of (matched_files, skipped_files)
    """
    pattern = re.compile(extension_pattern, re.IGNORECASE)
    results = []
    skipped = []
    for name in sorted(os.listdir(directory)):
        if pattern.search(name):
            results.append(os.path.join(directory, name))
        else:
            skipped.append(name)
    return results, skipped


def parse_metadata_arg(metadata: Optional[str]) -> Dict[str, Any]:
    """Parse --metadata as a JSON object."""
    if not metadata:
        return {}
    try:
        parsed = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--metadata must be valid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--metadata must be a JSON object")
    return parsed


def build_raw_file_metadata(
    location: Optional[str],
    source_system: Optional[str],
    metadata: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Build the metadata JSONB payload for raw_835_files."""
    raw_metadata = parse_metadata_arg(metadata)
    if location is not None:
        raw_metadata['location'] = location
    if source_system is not None:
        raw_metadata['source_system'] = source_system
    return raw_metadata or None


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------

def process_file(
    file_path: str,
    seed_db: bool,
    conn=None,
    output_dir: Optional[str] = None,
    extension_pattern: str = DEFAULT_EXTENSION_PATTERN,
    raw_file_metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Parse a single EDI 835 file and optionally seed all normalized DB tables.

    Returns a result dict with counts from parsing (and DB seeding if applicable).
    """
    file_name = os.path.basename(file_path)

    json_data = edi_835_parser.parse_to_json(file_path, extension_pattern=extension_pattern)

    transactions = json_data.get('interchange', {}).get('transactions', [])
    claims = sum(len(t.get('CLP_loop', [])) for t in transactions)
    service_lines = sum(
        len(c.get('SVC_loop', []))
        for t in transactions
        for c in t.get('CLP_loop', [])
    )

    result = {
        'file': file_name,
        'transactions': len(transactions),
        'claims': claims,
        'service_lines': service_lines,
    }

    if seed_db and conn is not None:
        from db.seed import seed_file
        from db.seed_bulk import seed_file_copy
        raw_edi = open(file_path, encoding='utf-8', errors='replace').read()
        file_id = generate_file_id(file_name)
        #db_stats = seed_file(conn, file_id, file_name, json_data, raw_edi)
        db_stats = seed_file_copy(
            conn,
            file_id,
            file_name,
            json_data,
            raw_edi,
            raw_file_metadata,
        )
        result['db_stats'] = db_stats

    if output_dir is not None:
        stem = os.path.splitext(file_name)[0]
        out_path = os.path.join(output_dir, f"{stem}_output.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        result['output_file'] = out_path

    return result


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_result(result: dict, seed_db: bool) -> None:
    parts = [
        f"{result['transactions']} transaction(s)",
        f"{result['claims']} claim(s)",
        f"{result['service_lines']} service line(s)",
    ]
    if seed_db and 'db_stats' in result:
        db = result['db_stats']
        parts.append(
            f"seeded: {db.get('claims', 0)} claims / "
            f"{db.get('service_lines', 0)} svc lines / "
            f"{db.get('cas_adjustments', 0)} adjustments"
        )
    if 'output_file' in result:
        parts.append(f"→ {result['output_file']}")
    print(f"  OK  {result['file']}: {', '.join(parts)}")


def print_summary(total: dict, file_count: int, errors: List[Tuple[str, str]]) -> None:
    print()
    print("=" * 60)
    print(f"Processed : {total['files']}/{file_count} file(s)")
    print(f"Transactions : {total['transactions']}")
    print(f"Claims       : {total['claims']}")
    print(f"Service Lines: {total['service_lines']}")
    if errors:
        print(f"Errors       : {len(errors)}")
        for fname, msg in errors:
            print(f"  FAIL  {fname}: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='EDI 835 Parser — parse files and optionally seed the database.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--file', metavar='PATH', help='Single EDI 835 file to process')
    source.add_argument('--dir', metavar='DIR', help='Directory of EDI 835 files to process')

    parser.add_argument(
        '--seed-db',
        action='store_true',
        help='Insert parsed data into all normalized database tables',
    )
    parser.add_argument(
        '--output-dir',
        metavar='DIR',
        help='Write parsed JSON for each file to this directory',
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity (default: INFO)',
    )
    parser.add_argument(
        '--extensions',
        default=DEFAULT_EXTENSION_PATTERN,
        help='File extensions to match. Accepts plain extensions (e.g. "DAT txt edi", '
             '"DAT,txt,edi", ".835") or a regex pattern.',
    )
    parser.add_argument(
        '--location',
        help='Location value to store in raw_835_files.metadata',
    )
    parser.add_argument(
        '--source-system',
        '--source_system',
        dest='source_system',
        help='Source system value to store in raw_835_files.metadata',
    )
    parser.add_argument(
        '--metadata',
        help='Additional raw_835_files metadata as a JSON object',
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    try:
        raw_file_metadata = build_raw_file_metadata(args.location, args.source_system, args.metadata)
    except ValueError as exc:
        parser.error(str(exc))

    # ------------------------------------------------------------------
    # Validate --output-dir
    # ------------------------------------------------------------------
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Resolve files to process
    # ------------------------------------------------------------------
    ext_pattern = extensions_to_regex(args.extensions)
    skipped_files: List[str] = []
    if args.file:
        if not os.path.isfile(args.file):
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        files = [args.file]
    else:
        directory = args.dir
        if not os.path.isdir(directory):
            print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
            sys.exit(1)
        files, skipped_files = find_edi_files(directory, ext_pattern)
        print(f"Found {len(files)} EDI file(s) in {directory}")
        if skipped_files:
            print(f"Skipped {len(skipped_files)} file(s) with non-matching extensions")
        if not files:
            # All files were skipped — write the results JSON if requested, then exit.
            if args.output_dir and skipped_files:
                skipped_results = [
                    {'FileName': name, 'Status': 'Skipped', 'Reason': 'Extension did not match pattern'}
                    for name in skipped_files
                ]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                results_path = os.path.join(args.output_dir, f'results_{timestamp}.json')
                with open(results_path, 'w', encoding='utf-8') as f:
                    json.dump(skipped_results, f, indent=2)
                print(f"Results saved → {results_path}")
            print(f"No EDI files matched in {directory}", file=sys.stderr)
            sys.exit(1)

    # ------------------------------------------------------------------
    # Open DB connection (shared across all files for efficiency)
    # ------------------------------------------------------------------
    conn: Optional[object] = None
    if args.seed_db:
        from db.connection import load_config, get_connection
        try:
            config = load_config()
            conn = get_connection(config)
            print(
                f"Connected to {config['DB_HOST']}:{config['DB_PORT']}"
                f"/{config['DB_NAME']} (schema={config['DB_SCHEMA']})"
            )
        except Exception as exc:
            print(f"ERROR: Database connection failed: {exc}", file=sys.stderr)
            sys.exit(1)

    # ------------------------------------------------------------------
    # Process each file
    # ------------------------------------------------------------------
    total = {'files': 0, 'transactions': 0, 'claims': 0, 'service_lines': 0}
    errors: List[Tuple[str, str]] = []
    file_results = []

    # Add skipped files to results
    for name in skipped_files:
        file_results.append({
            'FileName': name,
            'Status': 'Skipped',
            'Reason': 'Extension did not match pattern',
        })

    for file_path in files:
        file_name = os.path.basename(file_path)
        try:
            result = process_file(
                file_path,
                args.seed_db,
                conn,
                args.output_dir,
                ext_pattern,
                raw_file_metadata,
            )
            total['files'] += 1
            total['transactions'] += result['transactions']
            total['claims'] += result['claims']
            total['service_lines'] += result['service_lines']
            print_result(result, args.seed_db)
            entry = {
                'FileName': file_name,
                'Status': 'Success' if result['claims'] > 0 else 'Fail',
                'Transactions': result['transactions'],
                'Claims': result['claims'],
                'ServiceLines': result['service_lines'],
            }
            if result['claims'] == 0:
                entry['Reason'] = 'No claims found (file may contain only PLB adjustments or zero-pay transactions)'
            file_results.append(entry)
        except Exception as exc:
            logger.debug("Exception processing %s", file_name, exc_info=True)
            errors.append((file_name, str(exc)))
            print(f"  FAIL {file_name}: {exc}", file=sys.stderr)
            file_results.append({
                'FileName': file_name,
                'Status': 'Error',
                'Transactions': 0,
                'Claims': 0,
                'ServiceLines': 0,
                'Error': str(exc),
            })

    # ------------------------------------------------------------------
    # Cleanup and summary
    # ------------------------------------------------------------------
    if conn is not None:
        conn.close()

    print_summary(total, len(files), errors)

    # ------------------------------------------------------------------
    # Write results JSON to output directory
    # ------------------------------------------------------------------
    if args.output_dir and file_results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_path = os.path.join(args.output_dir, f'results_{timestamp}.json')
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(file_results, f, indent=2)
        print(f"Results saved → {results_path}")

    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
