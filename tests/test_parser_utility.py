"""
Tests for main.py utility behavior — covers the two cases from 835_Parser_Utilit_TestCases.csv.

Test Case 1: Custom --extensions argument should be combined with default extensions,
             not replace them.
Test Case 2: Result JSON must be written even when every file in the input directory
             is skipped due to a non-matching extension.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Add repo root to path so we can import main directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import DEFAULT_EXTENSION_PATTERN, extensions_to_regex, find_edi_files

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Test Case 1 — Custom extension regex should merge with default extensions
# ---------------------------------------------------------------------------

class TestCustomExtensionsMergedWithDefaults:
    """TC-1: Passing a custom --extensions value must not drop default extensions."""

    def test_extensions_to_regex_regex_input_includes_defaults(self):
        """extensions_to_regex() with a regex string should produce a pattern
        that still matches default extensions (.dat, .edi, no-extension, etc.)."""
        custom_regex = r'\.(uyt|pct)$'
        pattern = extensions_to_regex(custom_regex)

        # Custom extensions must match
        assert re.search(pattern, 'payment.uyt', re.IGNORECASE), \
            "Custom .uyt extension should be matched"
        assert re.search(pattern, 'remit.pct', re.IGNORECASE), \
            "Custom .pct extension should be matched"

        # Default extensions must also match
        assert re.search(pattern, 'file.DAT', re.IGNORECASE), \
            "Default .DAT extension should still be matched when custom regex is given"
        assert re.search(pattern, 'file.edi', re.IGNORECASE), \
            "Default .edi extension should still be matched when custom regex is given"
        assert re.search(pattern, 'file.txt', re.IGNORECASE), \
            "Default .txt extension should still be matched when custom regex is given"

    def test_extensions_to_regex_plain_input_includes_defaults(self):
        """extensions_to_regex() with plain extension strings should also include defaults."""
        pattern = extensions_to_regex('uyt pct')

        assert re.search(pattern, 'payment.uyt', re.IGNORECASE)
        assert re.search(pattern, 'remit.pct', re.IGNORECASE)
        assert re.search(pattern, 'file.DAT', re.IGNORECASE), \
            "Default .DAT extension should still be matched when plain extensions are given"
        assert re.search(pattern, 'file.edi', re.IGNORECASE), \
            "Default .edi extension should still be matched when plain extensions are given"

    def test_find_edi_files_custom_regex_includes_default_extension_files(self, tmp_path):
        """find_edi_files() with a custom-extension pattern should not skip default-extension files."""
        (tmp_path / 'payment.uyt').write_text('ISA*')
        (tmp_path / 'remit.pct').write_text('ISA*')
        (tmp_path / 'archive.DAT').write_text('ISA*')
        (tmp_path / 'claims.edi').write_text('ISA*')
        (tmp_path / 'report.xyz').write_text('not an EDI file')

        custom_regex = r'\.(uyt|pct)$'
        pattern = extensions_to_regex(custom_regex)
        matched, skipped = find_edi_files(str(tmp_path), pattern)
        matched_names = {os.path.basename(f) for f in matched}

        assert 'payment.uyt' in matched_names, ".uyt file should be matched"
        assert 'remit.pct' in matched_names, ".pct file should be matched"
        assert 'archive.DAT' in matched_names, ".DAT file should be matched (default extension)"
        assert 'claims.edi' in matched_names, ".edi file should be matched (default extension)"
        assert 'report.xyz' not in matched_names, ".xyz file should be skipped"
        assert 'report.xyz' in skipped, ".xyz file should appear in the skipped list"

    def test_cli_custom_extensions_processes_default_extension_files(self, tmp_path):
        """End-to-end: passing --extensions with a custom regex via CLI should still
        process files with default extensions."""
        input_dir = tmp_path / 'input'
        input_dir.mkdir()
        output_dir = tmp_path / 'output'
        output_dir.mkdir()

        # Copy a real EDI file so the parser can succeed on a .DAT file
        real_dat = REPO_ROOT / 'tests' / 'test_edi_835_files' / 'N3997028_EDI_20250825_20250825022552.DAT'
        if real_dat.exists():
            (input_dir / real_dat.name).write_bytes(real_dat.read_bytes())
        else:
            pytest.skip("Reference .DAT test file not found")

        result = subprocess.run(
            [
                sys.executable, str(REPO_ROOT / 'main.py'),
                '--dir', str(input_dir),
                '--output-dir', str(output_dir),
                '--extensions', r'\.(uyt|pct)$',
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        result_files = list(output_dir.glob('results_*.json'))
        assert result_files, "A results_*.json file should be written"

        entries = json.loads(result_files[0].read_text())
        statuses = {e['FileName']: e['Status'] for e in entries}

        assert real_dat.name in statuses, "The .DAT file should appear in the results"
        assert statuses[real_dat.name] == 'Success', \
            f".DAT file should be processed (status=Success), got: {statuses[real_dat.name]}"


# ---------------------------------------------------------------------------
# Test Case 2 — Result JSON generated even when all files are skipped
# ---------------------------------------------------------------------------

class TestResultJsonCreatedWhenAllFilesSkipped:
    """TC-2: result_*.json must be written even when every file is skipped."""

    def test_find_edi_files_all_skipped_returns_empty_matched(self, tmp_path):
        """find_edi_files() returns empty matched list when no file matches the pattern."""
        (tmp_path / 'data.xyz').write_text('ISA*')
        (tmp_path / 'report.abc').write_text('ISA*')

        pattern = DEFAULT_EXTENSION_PATTERN
        matched, skipped = find_edi_files(str(tmp_path), pattern)

        assert matched == [], "No files should match when extensions are non-standard"
        assert set(skipped) == {'data.xyz', 'report.abc'}, \
            "All files should appear in the skipped list"

    def test_cli_creates_result_json_when_all_files_skipped(self, tmp_path):
        """End-to-end: CLI must write a results_*.json with 'Skipped' entries even
        when every file in the input directory fails the extension filter."""
        input_dir = tmp_path / 'input'
        input_dir.mkdir()
        output_dir = tmp_path / 'output'
        output_dir.mkdir()

        # Create files whose extensions will never match the filter
        (input_dir / 'payment_file.xyz').write_text('not parsed')
        (input_dir / 'remit_data.abc').write_text('not parsed')

        result = subprocess.run(
            [
                sys.executable, str(REPO_ROOT / 'main.py'),
                '--dir', str(input_dir),
                '--output-dir', str(output_dir),
                '--extensions', r'\.(dat|edi)$',
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        result_files = list(output_dir.glob('results_*.json'))
        assert result_files, \
            "results_*.json should be created even when all files are skipped"

        entries = json.loads(result_files[0].read_text())
        assert len(entries) == 2, "Both skipped files should appear in the JSON"

        for entry in entries:
            assert entry['Status'] == 'Skipped', \
                f"Expected Status='Skipped' for {entry['FileName']}, got '{entry['Status']}'"

    def test_cli_result_json_contains_skipped_filenames(self, tmp_path):
        """Skipped entries in the result JSON must include the original filenames."""
        input_dir = tmp_path / 'input'
        input_dir.mkdir()
        output_dir = tmp_path / 'output'
        output_dir.mkdir()

        (input_dir / 'file_alpha.xyz').write_text('x')
        (input_dir / 'file_beta.xyz').write_text('x')

        subprocess.run(
            [
                sys.executable, str(REPO_ROOT / 'main.py'),
                '--dir', str(input_dir),
                '--output-dir', str(output_dir),
                '--extensions', r'\.(dat|edi)$',
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        result_files = list(output_dir.glob('results_*.json'))
        assert result_files, "results_*.json should be created"

        entries = json.loads(result_files[0].read_text())
        file_names = {e['FileName'] for e in entries}

        assert 'file_alpha.xyz' in file_names, "file_alpha.xyz should appear in results"
        assert 'file_beta.xyz' in file_names, "file_beta.xyz should appear in results"
