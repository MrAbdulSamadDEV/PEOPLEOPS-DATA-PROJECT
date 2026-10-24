"""Stage 1 - Load raw data from CSV and JSON files into raw.sqlite, idempotent."""
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from config import DATA_DIR, RAW_DB, ANALYSIS_START, ANALYSIS_END
from db import get_engine, run_sql_script


def file_hash(path):
    """Compute SHA-256 hash of a file to detect changes."""
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_csv(table_name, filepath, key_column=None):
    """Load a CSV file into the raw schema. Idempotent: skips if file hash unchanged."""
    engine = get_engine()
    
    # Create hash tracking table if not exists
    run_sql_script("""
        CREATE TABLE IF NOT EXISTS raw.file_hashes (
            filename TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL
        );
    """)
    
    # Check if file changed
    current_hash = file_hash(filepath)
    with engine.connect() as conn:
        existing_hash = conn.exec_driver_sql(
            "SELECT file_hash FROM raw.file_hashes WHERE filename = ?",
            (table_name,)
        ).scalar()
    
    if existing_hash == current_hash:
        print(f"  {table_name}: unchanged (hash match), skipping")
        return
    
    # Load file
    print(f"  {table_name}: loading {filepath.name}")
    df = pd.read_csv(filepath, dtype=str, keep_default_na=False, na_values=[''])
    
    # Drop existing table
    run_sql_script(f"DROP TABLE IF EXISTS raw.{table_name}")
    
    # Create table with all TEXT columns
    cols = ", ".join(f"{col} TEXT" for col in df.columns)
    run_sql_script(f"CREATE TABLE raw.{table_name} ({cols});")
    
    # Insert data
    df.to_sql(table_name, engine, schema='raw', if_exists='append', index=False, method='multi')
    
    # Update hash
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT OR REPLACE INTO raw.file_hashes VALUES (?, ?)",
            (table_name, current_hash)
        )
    
    print(f"    {len(df)} rows loaded")


def load_json(table_name, filepath):
    """Load a JSON file (array of objects) into raw schema as TEXT payload."""
    engine = get_engine()
    
    # Check hash
    current_hash = file_hash(filepath)
    with engine.connect() as conn:
        existing_hash = conn.exec_driver_sql(
            "SELECT file_hash FROM raw.file_hashes WHERE filename = ?",
            (table_name,)
        ).scalar()
    
    if existing_hash == current_hash:
        print(f"  {table_name}: unchanged (hash match), skipping")
        return
    
    # Load JSON
    print(f"  {table_name}: loading {filepath.name}")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    # Drop existing table
    run_sql_script(f"DROP TABLE IF EXISTS raw.{table_name}")
    
    # Create table with TEXT payload
    run_sql_script(f"""
        CREATE TABLE raw.{table_name} (
            record_id INTEGER PRIMARY KEY,
            payload TEXT NOT NULL
        );
    """)
    
    # Insert data
    with engine.begin() as conn:
        for i, record in enumerate(data, start=1):
            payload = json.dumps(record, separators=(',', ':'))
            conn.exec_driver_sql(
                f"INSERT INTO raw.{table_name} VALUES (?, ?)",
                (i, payload)
            )
    
    # Update hash
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT OR REPLACE INTO raw.file_hashes VALUES (?, ?)",
            (table_name, current_hash)
        )
    
    print(f"    {len(data)} records loaded")


def run(force=False):
    """Load all raw data files. If force=True, reload everything."""
    print("Stage 1 - Load raw data")
    
    if force:
        run_sql_script("DROP TABLE IF EXISTS raw.file_hashes;")
        print("  forcing reload of all files")
    
    # Load CSV files
    load_csv("employees", DATA_DIR / "employees.csv")
    load_csv("employment_history", DATA_DIR / "employment_history.csv")
    load_csv("departments", DATA_DIR / "departments.csv")
    load_csv("shift_roster", DATA_DIR / "shift_roster.csv")
    load_csv("biometric_punches", DATA_DIR / "biometric_punches.csv")
    load_csv("device_mapping", DATA_DIR / "device_mapping.csv")
    load_csv("holidays", DATA_DIR / "holidays.csv")
    load_csv("payroll_lines", DATA_DIR / "payroll_lines.csv")
    load_csv("overtime_requests", DATA_DIR / "overtime_requests.csv")
    load_csv("applications", DATA_DIR / "applications.csv")
    
    # Load JSON files
    load_json("leaves", DATA_DIR / "leave_requests.json")
    load_json("shifts", DATA_DIR / "shifts.json")
    
    print("Stage 1 complete")
