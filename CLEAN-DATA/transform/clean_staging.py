"""Stage 2 - Clean and standardize raw data into staging tables."""
import json
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from config import ANALYSIS_START, ANALYSIS_END, PLANT_NAMES
from db import get_engine, run_sql_script


def create_staging_schema():
    """Create staging schema and rejected tables."""
    run_sql_script("""
        -- Create staging schema tables
        CREATE TABLE IF NOT EXISTS staging.employees (
            emp_id TEXT PRIMARY KEY,
            full_name TEXT,
            gender TEXT,
            date_of_birth TEXT,
            hire_date TEXT NOT NULL,
            separation_date TEXT,
            plant TEXT,
            current_department TEXT,
            designation TEXT,
            grade TEXT,
            basic_salary REAL,
            employment_type TEXT,
            updated_at TEXT
        );
        
        CREATE TABLE IF NOT EXISTS staging.employment_history (
            emp_id TEXT NOT NULL,
            effective_from TEXT NOT NULL,
            effective_to TEXT NOT NULL,
            department TEXT,
            designation TEXT,
            grade TEXT,
            basic_salary REAL,
            change_reason TEXT,
            PRIMARY KEY (emp_id, effective_from)
        );
        
        CREATE TABLE IF NOT EXISTS staging.departments (
            dept_id TEXT PRIMARY KEY,
            plant TEXT,
            dept_name TEXT,
            cost_center TEXT
        );
        
        CREATE TABLE IF NOT EXISTS staging.punches_clean (
            punch_id TEXT PRIMARY KEY,
            emp_id TEXT NOT NULL,
            device_id TEXT,
            punch_time TEXT NOT NULL,
            punch_type TEXT
        );
        
        CREATE TABLE IF NOT EXISTS staging.roster_daily (
            emp_id TEXT NOT NULL,
            work_date TEXT NOT NULL,
            shift_code TEXT,
            PRIMARY KEY (emp_id, work_date)
        );
        
        CREATE TABLE IF NOT EXISTS staging.attendance_daily (
            emp_id TEXT NOT NULL,
            work_date TEXT NOT NULL,
            shift_code TEXT,
            status TEXT,
            punch_count INTEGER,
            check_in TEXT,
            check_out TEXT,
            worked_hours REAL,
            late_minutes REAL,
            early_minutes REAL,
            overtime_hours REAL,
            PRIMARY KEY (emp_id, work_date)
        );
        
        CREATE TABLE IF NOT EXISTS staging.leave_requests (
            request_id TEXT PRIMARY KEY,
            emp_id TEXT,
            leave_from TEXT,
            leave_to TEXT,
            leave_type TEXT,
            status TEXT
        );
        
        CREATE TABLE IF NOT EXISTS staging.leave_approval_steps (
            step_id TEXT PRIMARY KEY,
            request_id TEXT,
            action TEXT
        );
        
        CREATE TABLE IF NOT EXISTS staging.overtime_requests (
            request_id TEXT PRIMARY KEY,
            emp_id TEXT,
            request_date TEXT,
            status TEXT,
            approved_hours REAL
        );
        
        -- Rejected tables for audit
        CREATE TABLE IF NOT EXISTS staging.rejected_employees (
            emp_id TEXT,
            reason TEXT,
            raw_data TEXT
        );
        
        CREATE TABLE IF NOT EXISTS staging.rejected_punches (
            punch_id TEXT,
            emp_id TEXT,
            reason TEXT,
            punch_time TEXT
        );
        
        CREATE TABLE IF NOT EXISTS staging.rejected_employment_history (
            emp_id TEXT,
            effective_from TEXT,
            reason TEXT
        );
    """)


def clean_employees():
    """Clean and deduplicate employees."""
    print("  cleaning employees")
    engine = get_engine()
    
    # Load raw employees
    df = pd.read_sql("SELECT * FROM raw.employees", engine)
    
    # Handle duplicates: keep latest by updated_at
    if 'updated_at' in df.columns:
        df = df.sort_values('updated_at').drop_duplicates('emp_id', keep='last')
        rejected = pd.read_sql("SELECT * FROM raw.employees", engine).drop_duplicates('emp_id', keep=False)
        if len(rejected) > 0:
            with engine.begin() as conn:
                for _, row in rejected.iterrows():
                    conn.exec_driver_sql(
                        "INSERT INTO staging.rejected_employees VALUES (?, ?, ?)",
                        (row.get('emp_id'), 'DUPLICATE_EMP_ID', json.dumps(row.to_dict(), default=str))
                    )
    
    # Standardize columns
    df_clean = pd.DataFrame()
    df_clean['emp_id'] = df.get('emp_id', '')
    df_clean['full_name'] = df.get('full_name', '')
    df_clean['gender'] = df.get('gender', '')
    df_clean['date_of_birth'] = df.get('date_of_birth', '')
    df_clean['hire_date'] = df.get('hire_date', '')  # TODO: parse different date formats
    df_clean['separation_date'] = df.get('separation_date', '')
    df_clean['plant'] = df.get('plant', '')
    df_clean['current_department'] = df.get('department', '')
    df_clean['designation'] = df.get('designation', '')
    df_clean['grade'] = df.get('grade', '')
    df_clean['basic_salary'] = pd.to_numeric(df.get('basic_salary', 0), errors='coerce')
    df_clean['employment_type'] = df.get('employment_type', '')
    df_clean['updated_at'] = df.get('updated_at', '')
    
    # Load to staging
    df_clean.to_sql('employees', engine, schema='staging', if_exists='replace', index=False)


def clean_employment_history():
    """Clean employment history."""
    print("  cleaning employment history")
    engine = get_engine()
    
    df = pd.read_sql("SELECT * FROM raw.employment_history", engine)
    df_clean = pd.DataFrame()
    df_clean['emp_id'] = df.get('emp_id', '')
    df_clean['effective_from'] = df.get('effective_from', '')
    df_clean['effective_to'] = df.get('effective_to', '')
    df_clean['department'] = df.get('department', '')
    df_clean['designation'] = df.get('designation', '')
    df_clean['grade'] = df.get('grade', '')
    df_clean['basic_salary'] = pd.to_numeric(df.get('basic_salary', 0), errors='coerce')
    df_clean['change_reason'] = df.get('change_reason', '')
    
    df_clean.to_sql('employment_history', engine, schema='staging', if_exists='replace', index=False)


def clean_departments():
    """Clean departments."""
    print("  cleaning departments")
    engine = get_engine()
    
    df = pd.read_sql("SELECT * FROM raw.departments", engine)
    df_clean = pd.DataFrame()
    df_clean['dept_id'] = df.get('dept_id', '')
    df_clean['plant'] = df.get('plant', '')
    df_clean['dept_name'] = df.get('dept_name', '')
    df_clean['cost_center'] = df.get('cost_center', '')
    
    df_clean.to_sql('departments', engine, schema='staging', if_exists='replace', index=False)


def clean_punches():
    """Clean biometric punches."""
    print("  cleaning punches")
    engine = get_engine()
    
    df = pd.read_sql("SELECT * FROM raw.biometric_punches", engine)
    
    # Remove duplicates (punches within 2 minutes)
    df_clean = pd.DataFrame()
    df_clean['punch_id'] = df.get('punch_id', '')
    df_clean['emp_id'] = df.get('emp_id', '')
    df_clean['device_id'] = df.get('device_id', '')
    df_clean['punch_time'] = df.get('punch_time', '')
    df_clean['punch_type'] = df.get('punch_type', '')
    
    # Deduplicate
    df_clean = df_clean.drop_duplicates('punch_id')
    
    df_clean.to_sql('punches_clean', engine, schema='staging', if_exists='replace', index=False)


def clean_roster():
    """Clean shift roster into daily records."""
    print("  cleaning shift roster")
    engine = get_engine()
    
    df = pd.read_sql("SELECT * FROM raw.shift_roster", engine)
    
    # Expand weekly roster to daily - each row is for a week starting on week_start
    rows = []
    for _, row in df.iterrows():
        emp_id = row.get('emp_id', '')
        shift_code = row.get('shift_code', 'GEN')
        week_start_str = row.get('week_start', '')
        
        if emp_id and week_start_str:
            try:
                # week_start is a Monday, expand to 7 days
                week_start = pd.to_datetime(week_start_str)
                for day_offset in range(7):
                    work_date = (week_start + pd.Timedelta(days=day_offset)).strftime('%Y-%m-%d')
                    rows.append({
                        'emp_id': emp_id,
                        'work_date': work_date,
                        'shift_code': shift_code
                    })
            except Exception as e:
                pass
    
    if rows:
        df_roster = pd.DataFrame(rows)
        df_roster.to_sql('roster_daily', engine, schema='staging', if_exists='replace', index=False)
    else:
        # Create empty table
        run_sql_script("""
            CREATE TABLE IF NOT EXISTS staging.roster_daily (
                emp_id TEXT NOT NULL,
                work_date TEXT NOT NULL,
                shift_code TEXT,
                PRIMARY KEY (emp_id, work_date)
            );
        """)


def clean_leaves():
    """Clean leave requests."""
    print("  cleaning leave requests")
    engine = get_engine()
    
    # Load JSON leaves
    leaves = []
    with engine.connect() as conn:
        result = conn.exec_driver_sql("SELECT record_id, payload FROM raw.leaves")
        for rec_id, payload in result:
            try:
                data = json.loads(payload)
                # Extract nested fields
                leave_req = {
                    'request_id': data.get('request_id', str(rec_id)),
                    'emp_id': data.get('employee', {}).get('emp_id', ''),
                    'leave_from': data.get('leave', {}).get('from', ''),
                    'leave_to': data.get('leave', {}).get('to', ''),
                    'leave_type': data.get('leave', {}).get('type', ''),
                }
                # Determine status from approvals
                approvals = data.get('approvals', [])
                if approvals:
                    last_action = approvals[-1].get('action', 'Pending')
                    leave_req['status'] = last_action
                else:
                    leave_req['status'] = 'Pending'
                leaves.append(leave_req)
            except Exception as e:
                pass
    
    if leaves:
        df = pd.DataFrame(leaves)
        df_clean = pd.DataFrame()
        df_clean['request_id'] = df.get('request_id', '')
        df_clean['emp_id'] = df.get('emp_id', '')
        df_clean['leave_from'] = df.get('leave_from', '')
        df_clean['leave_to'] = df.get('leave_to', '')
        df_clean['leave_type'] = df.get('leave_type', '')
        df_clean['status'] = df.get('status', '')
        
        df_clean.to_sql('leave_requests', engine, schema='staging', if_exists='replace', index=False)


def clean_overtime():
    """Clean overtime requests."""
    print("  cleaning overtime requests")
    engine = get_engine()
    
    df = pd.read_sql("SELECT * FROM raw.overtime_requests", engine)
    df_clean = pd.DataFrame()
    df_clean['request_id'] = df.get('request_id', '')
    df_clean['emp_id'] = df.get('emp_id', '')
    df_clean['request_date'] = df.get('request_date', '')
    df_clean['status'] = df.get('status', '')
    df_clean['approved_hours'] = pd.to_numeric(df.get('approved_hours', 0), errors='coerce')
    
    df_clean.to_sql('overtime_requests', engine, schema='staging', if_exists='replace', index=False)


def run():
    """Stage 2: Create staging schema and clean data."""
    print("Stage 2 - Clean and standardize data")
    
    create_staging_schema()
    clean_employees()
    clean_employment_history()
    clean_departments()
    clean_punches()
    clean_roster()
    clean_leaves()
    clean_overtime()
    
    print("Stage 2 complete")
