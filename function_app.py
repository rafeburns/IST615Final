"""
Azure Function for automated CSV processing pipeline.
Triggered by Blob Storage upload — cleans, validates, and summarizes CSV data.
"""

import json
import csv
import io
import os
import logging
from datetime import datetime

import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

CONNECT_STR = os.environ.get("AzureWebJobsStorage", "")
OUTPUT_CONTAINER = os.environ.get("OUTPUT_CONTAINER", "output")


@app.blob_trigger(
    arg_name="inputblob",
    path="uploads/{name}",
    connection="AzureWebJobsStorage",
)
def process_csv(inputblob: func.InputStream):
    """Triggered when a CSV is uploaded to the 'uploads' container."""
    filename = inputblob.name  # e.g. "uploads/survey.csv"
    logging.info(f"Processing blob: {filename}")

    # 1. Read the CSV
    raw_csv = inputblob.read().decode("utf-8")

    # 2. Clean and analyze
    cleaned_rows, summary = run_pipeline(raw_csv)

    # 3. Build output names
    base_name = os.path.splitext(os.path.basename(filename))[0]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    cleaned_name = f"cleaned/{base_name}_{timestamp}.csv"
    summary_name = f"summaries/{base_name}_{timestamp}_summary.json"

    # 4. Upload results to output container
    blob_service = BlobServiceClient.from_connection_string(CONNECT_STR)
    container = blob_service.get_container_client(OUTPUT_CONTAINER)

    # Ensure output container exists
    try:
        container.create_container()
    except Exception:
        pass  # already exists

    container.upload_blob(cleaned_name, rows_to_csv(cleaned_rows), overwrite=True)
    logging.info(f"Cleaned CSV saved: {cleaned_name}")

    container.upload_blob(summary_name, json.dumps(summary, indent=2), overwrite=True)
    logging.info(f"Summary saved: {summary_name}")
    logging.info(f"Done — {summary['cleaned_row_count']}/{summary['original_row_count']} rows kept")


# ──────────────────────────────────────────────
#  Data processing
# ──────────────────────────────────────────────

def run_pipeline(raw_csv):
    """Clean and analyze CSV data. Returns (cleaned_rows, summary_dict)."""
    reader = csv.DictReader(io.StringIO(raw_csv))
    headers = reader.fieldnames
    if not headers:
        raise ValueError("CSV file has no headers")

    rows = list(reader)
    total_rows = len(rows)
    logging.info(f"Parsed {total_rows} rows, columns: {headers}")

    # --- Cleaning ---
    cleaned = []
    dropped = 0
    duplicates_removed = 0
    seen = set()

    for row in rows:
        # Strip whitespace
        row = {k: v.strip() if v else "" for k, v in row.items()}

        # Drop fully empty rows
        if all(v == "" for v in row.values()):
            dropped += 1
            continue

        # Remove duplicates
        key = tuple(row.values())
        if key in seen:
            duplicates_removed += 1
            continue
        seen.add(key)

        # Fill missing values
        for col in row:
            if row[col] == "":
                row[col] = _fill_default(col, rows)

        cleaned.append(row)

    # --- Analysis on numeric columns ---
    numeric_cols = _detect_numeric_columns(cleaned, headers)
    stats = {}
    for col in numeric_cols:
        values = []
        for r in cleaned:
            try:
                values.append(float(r[col]))
            except (ValueError, TypeError):
                continue
        if values:
            stats[col] = {
                "count": len(values),
                "mean": round(sum(values) / len(values), 2),
                "min": min(values),
                "max": max(values),
                "sum": round(sum(values), 2),
            }

    summary = {
        "original_row_count": total_rows,
        "cleaned_row_count": len(cleaned),
        "rows_dropped_empty": dropped,
        "duplicates_removed": duplicates_removed,
        "columns": headers,
        "numeric_column_stats": stats,
    }

    return cleaned, summary


def _detect_numeric_columns(rows, headers):
    """Columns where >50% of non-empty values parse as numbers."""
    numeric = []
    for col in headers:
        num_count = 0
        total = 0
        for r in rows:
            val = r.get(col, "")
            if val in ("", "N/A"):
                continue
            total += 1
            try:
                float(val)
                num_count += 1
            except ValueError:
                pass
        if total > 0 and (num_count / total) > 0.5:
            numeric.append(col)
    return numeric


def _fill_default(column_name, all_rows):
    """'0' if column is mostly numeric, else 'N/A'."""
    num_count = 0
    total = 0
    for r in all_rows:
        val = r.get(column_name, "").strip()
        if val == "":
            continue
        total += 1
        try:
            float(val)
            num_count += 1
        except ValueError:
            pass
    if total > 0 and (num_count / total) > 0.5:
        return "0"
    return "N/A"


def rows_to_csv(rows):
    """Convert list of dicts to CSV string."""
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
