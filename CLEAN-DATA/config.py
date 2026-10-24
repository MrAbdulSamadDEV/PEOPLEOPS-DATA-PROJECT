"""Configuration: paths, database, and business constants."""
import os
from pathlib import Path

# Paths relative to this file
PROJECT_DIR = Path(__file__).resolve().parent
DB_DIR = PROJECT_DIR / "db"
DATA_DIR = PROJECT_DIR / "data"
WAREHOUSE_DIR = PROJECT_DIR / "warehouse"
ANALYTICS_DIR = PROJECT_DIR / "analytics"
OUTPUT_DIR = PROJECT_DIR / "output"

# Ensure output directories exist
DB_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(ANALYTICS_DIR / "results").mkdir(parents=True, exist_ok=True)

# Database files
RAW_DB = DB_DIR / "raw.sqlite"
STAGING_DB = DB_DIR / "staging.sqlite"
WAREHOUSE_DB = DB_DIR / "warehouse.sqlite"

# Analysis period
ANALYSIS_START = "2026-04-01"
ANALYSIS_END = "2026-09-30"

# Plant and department mapping
PLANT_NAMES = {
    "MAIN": "Main Plant",
    "STITCHING": "Stitching Unit",
}

# Shift definitions (in minutes from midnight)
SHIFT_DEFS = {
    "DAY": {"start": 360, "end": 900, "name": "Day", "crosses_midnight": False, "grace": 10},  # 6:00-15:00
    "EVE": {"start": 840, "end": 1320, "name": "Evening", "crosses_midnight": False, "grace": 10},  # 14:00-22:00
    "NIGHT": {"start": 1320, "end": 360, "name": "Night", "crosses_midnight": True, "grace": 10},  # 22:00-6:00 (next day)
    "GEN": {"start": 360, "end": 1020, "name": "General", "crosses_midnight": False, "grace": 10},  # 6:00-17:00
}

# Leave entitlements per employment type
LEAVE_ENTITLEMENTS = {
    "Permanent": 21,
    "Temporary": 10,
    "Contractual": 0,
}

# Allowed values for data validation
ALLOWED_ATTENDANCE_STATUS = ["Present", "Absent", "On Leave", "Holiday", "Weekly Off", "Missing Punch"]
ALLOWED_LEAVE_TYPES = ["Annual", "Casual", "Sick"]
ALLOWED_EMPLOYMENT_STATUS = ["Active", "Separated"]
ALLOWED_COMPONENTS = ["BASIC", "HOUSE_RENT", "MEDICAL", "CONVEYANCE", "OVERTIME", "INCOME_TAX", "EOBI", "ABSENCE_DEDUCTION", "LOAN_INSTALLMENT"]
ALLOWED_COMPONENT_TYPES = ["EARNING", "DEDUCTION"]
