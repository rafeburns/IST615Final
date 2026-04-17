"""
Local test — runs the CSV processing pipeline without Azure.
Usage: python test_local.py sample_data.csv
"""

import sys
import json
from function_app import run_pipeline, rows_to_csv

if len(sys.argv) < 2:
    print("Usage: python test_local.py <csv_file>")
    sys.exit(1)

with open(sys.argv[1], "r") as f:
    raw = f.read()

cleaned, summary = run_pipeline(raw)

print("=== Summary ===")
print(json.dumps(summary, indent=2))
print(f"\n=== Cleaned CSV ({len(cleaned)} rows) ===")
print(rows_to_csv(cleaned))
