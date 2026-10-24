# Indus Weave Textiles: HR Data Pipeline - Windows Quick Start

## One-Click Setup

Simply **double-click `RUN_PROJECT.bat`** to run the entire pipeline automatically.

The batch file will:
1. ✓ Check if Python is installed
2. ✓ Create a virtual environment (if needed)
3. ✓ Install all dependencies
4. ✓ Run the complete data pipeline
5. ✓ Display results and keep the window open for review

**Expected duration**: ~1-2 minutes

## What Gets Created

After running, you'll find:

- **`db/warehouse.sqlite`** - Main data warehouse (star schema)
- **`db/raw.sqlite`** - Raw data (unchanged from source)
- **`db/staging.sqlite`** - Cleaned and transformed data
- **`analytics/results/`** - 10 CSV files with answers to business questions
- **`output/`** - Any export files

## What the Pipeline Does

### Stage 1: Raw Data Ingestion
- Loads 12 CSV and JSON files from `data/`
- Stores everything as-is in the raw database
- Tracks file hashes to skip unchanged data

### Stage 2: Data Cleaning
- Handles duplicates, date format variations, and missing values
- Standardizes employee, department, and punch records
- Creates rejected tables with audit trails

### Stage 3: Business Logic
- Builds daily attendance records from punches and roster
- Calculates worked hours, overtime, and leave balances
- Applies shift rotation rules

### Stage 4: Warehouse Star Schema
- Creates fact tables (attendance, leave, payroll, overtime)
- Creates dimension tables (employee, date, department, shift)
- Implements SCD Type 2 for employee history tracking

### Stage 5: Analytics
- Runs 10 SQL queries answering business questions:
  - Q1: Month-end headcount by plant and department
  - Q2: Employee attrition
  - Q3: Absenteeism rates
  - Q4: Late arrivals analysis
  - Q5: Overtime reconciliation
  - Q6: Cases where paid hours exceed computed
  - Q7: Attendance anomalies
  - Q8: Post-separation payments
  - Q9: Payroll cost analysis
  - Q10: Annual leave overuse

### Stage 6: Quality Assurance
- 78 data quality checks
- Independent pandas recount verification
- Results saved to `warehouse.dq_results` table

## Troubleshooting

### Python Not Found
```
[FAIL] Python is not installed or not in PATH
```
**Solution**: Download Python 3.10+ from https://www.python.org and reinstall, making sure to check "Add Python to PATH".

### Virtual Environment Fails
```
[FAIL] Failed to create virtual environment
```
**Solution**: Delete the `venv` folder and try again.

### Dependency Installation Fails
```
[FAIL] Failed to install dependencies
```
**Solution**: 
- Make sure you have internet access
- Check that pip is working: `python -m pip --version`
- Delete `venv` and try again

### Pipeline Fails with Database Error
```
[FAIL] Pipeline failed
```
**Solution**: 
- The error message above will show what went wrong
- Usually means data is missing or corrupted
- Try deleting `db/` folder and running again

## Advanced: Running from Command Line

If you prefer, you can also run from CMD:

```cmd
cd path\to\CLEAN-DATA
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py --clean
```

Options:
- `python run_pipeline.py` - Run pipeline (skip unchanged raw files)
- `python run_pipeline.py --clean` - Force full reload from raw data

## Key Files

- **`run_pipeline.py`** - Main entry point (stages 1-6)
- **`config.py`** - Configuration (paths, analysis dates, business rules)
- **`db.py`** - Database connection and utilities
- **`ingestion/`** - Stage 1: raw data loading
- **`transform/`** - Stages 2-3: cleaning and business logic
- **`warehouse/`** - Stage 4: star schema building
- **`analytics/`** - Stage 5: business question queries
- **`quality/`** - Stage 6: data quality checks
- **`data/`** - Input CSV/JSON files
- **`db/`** - SQLite database files (created during run)

## Output Interpretation

### analytics/results/q01_results.csv (Headcount)
Shows employee count by month, plant, and department for April-September 2026.

### analytics/results/q02_results.csv (Attrition)
Employees who separated during the period with separation dates.

### analytics/results/q03_results.csv (Absenteeism)
Monthly absence rates by employee and department.

### ... (remaining queries in output)

### warehouse.dq_results (Quality Checks)
SQL table with 78+ data quality checks. Look for:
- `status = 'PASS'` - Everything OK
- `status = 'WARN'` - Known issue (documented)
- `status = 'FAIL'` - Data problem (pipeline stops)

## Architecture

```
Raw (12 files)
    ↓
Stage 1: Raw DB (all TEXT, hashes for idempotency)
    ↓
Stage 2: Staging DB (cleaning, dedup, standardization)
    ↓
Stage 3: Staging DB (business logic, daily attendance)
    ↓
Stage 4: Warehouse DB (star schema: facts + dimensions)
    ↓
Stage 5: Analytics (10 CSV reports)
    ↓
Stage 6: Quality Checks (78 rules, results in DQ table)
```

## About the Data

**Analysis Period**: April 1 - September 30, 2026 (6 months)

**Source Files**:
- `employees.csv` - Current employee master data
- `employment_history.csv` - Salary, department, and designation changes
- `departments.csv` - Department hierarchy and cost centers
- `shift_roster.csv` - Weekly shift assignments
- `biometric_punches.csv` - ~1 million punch records
- `device_mapping.csv` - Device to user mapping
- `holidays.csv` - Plant holidays
- `payroll_lines.csv` - Payroll components and amounts
- `overtime_requests.csv` - Overtime approvals
- `applications.csv` - Job applications (optional)
- `leave_requests.json` - Leave requests with approvals
- `shifts.json` - Shift definitions

## Known Limitations

1. **Night-shift checkout after separation**: 20 punches after separation dates (documented warning)
2. **Attendance grain**: One row per employee per day of employment (April-September)
3. **Late/early minutes**: Counted only on working days with >10 min gap
4. **Overtime rounding**: Whole half-hours, rounded down
5. **Incremental load**: Not fully implemented (use `--clean` to reload all data)

## Support

For detailed documentation, see the original `README.md` file.

For questions about the business logic, rules, and data cleaning decisions, refer to the README.md Design Decisions section.
