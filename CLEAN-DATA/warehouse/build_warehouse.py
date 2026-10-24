"""Stage 4 - Build star schema warehouse."""
from pathlib import Path
import pandas as pd
from sqlalchemy import text

from config import WAREHOUSE_DIR, ANALYSIS_START, ANALYSIS_END
from db import get_engine, run_sql_file, run_sql_script


def run():
    """Stage 4: Build star schema and load data."""
    print("Stage 4 - Build warehouse")
    
    # Create schema from DDL
    schema_file = WAREHOUSE_DIR / "ddl" / "schema.sql"
    print("  creating warehouse schema")
    run_sql_file(schema_file)
    
    # Load dimensions
    load_dim_date()
    load_dim_department()
    load_dim_shift()
    load_dim_employee()
    
    # Load facts
    load_fact_attendance_daily()
    load_fact_leave_day()
    load_fact_overtime_approved()
    load_fact_payroll_line()
    
    # Create views
    create_views()
    
    print("Stage 4 complete")


def load_dim_date():
    """Load dimension date from analysis period."""
    print("  loading dim_date")
    engine = get_engine()
    
    # Generate all dates in analysis period
    dates = pd.date_range(start=ANALYSIS_START, end=ANALYSIS_END, freq='D')
    rows = []
    for d in dates:
        rows.append({
            'date_key': int(d.strftime('%Y%m%d')),
            'full_date': d.strftime('%Y-%m-%d'),
            'year': d.year,
            'month_number': d.month,
            'month_key': d.strftime('%Y-%m'),
            'month_start': d.strftime('%Y-%m-01'),
            'month_end': (d + pd.tseries.offsets.MonthEnd(0)).strftime('%Y-%m-%d'),
            'day_of_week': d.weekday(),  # Monday=0, Sunday=6 (will convert to Sunday=0 below)
            'is_sunday': 1 if d.weekday() == 6 else 0,
            'is_month_end': 1 if d.day == (d + pd.tseries.offsets.MonthEnd(0)).day else 0,
        })
    
    df = pd.DataFrame(rows)
    df['day_of_week'] = (df['day_of_week'] + 1) % 7  # Convert to Sunday=0
    
    df.to_sql('dim_date', engine, schema='warehouse', if_exists='replace', index=False)


def load_dim_department():
    """Load department dimension."""
    print("  loading dim_department")
    engine = get_engine()
    
    df = pd.read_sql("SELECT DISTINCT * FROM staging.departments", engine)
    df_dim = pd.DataFrame({
        'dept_id': df.get('dept_id', ''),
        'dept_name': df.get('dept_name', ''),
        'plant': df.get('plant', ''),
        'cost_center': df.get('cost_center', ''),
        'previous_name': '',
        'renamed_on': None,
    })
    
    df_dim.to_sql('dim_department', engine, schema='warehouse', if_exists='replace', index=False)


def load_dim_shift():
    """Load shift dimension."""
    print("  loading dim_shift")
    engine = get_engine()
    
    shifts = [
        {'shift_code': 'DAY', 'shift_name': 'Day', 'start_time': '06:00', 'end_time': '15:00', 'crosses_midnight': 0, 'grace_minutes': 10},
        {'shift_code': 'EVE', 'shift_name': 'Evening', 'start_time': '14:00', 'end_time': '22:00', 'crosses_midnight': 0, 'grace_minutes': 10},
        {'shift_code': 'NIGHT', 'shift_name': 'Night', 'start_time': '22:00', 'end_time': '06:00', 'crosses_midnight': 1, 'grace_minutes': 10},
        {'shift_code': 'GEN', 'shift_name': 'General', 'start_time': '06:00', 'end_time': '17:00', 'crosses_midnight': 0, 'grace_minutes': 10},
    ]
    
    df = pd.DataFrame(shifts)
    df.to_sql('dim_shift', engine, schema='warehouse', if_exists='replace', index=False)


def load_dim_employee():
    """Load employee dimension (SCD Type 2)."""
    print("  loading dim_employee")
    engine = get_engine()
    
    run_sql_script("""
        INSERT INTO warehouse.dim_employee (
            emp_id, full_name, gender, date_of_birth, hire_date, separation_date,
            plant, dept_id, designation, grade, basic_salary, employment_type,
            employment_status, annual_leave_entitlement, change_reason,
            valid_from, valid_to, is_current
        )
        SELECT
            e.emp_id,
            e.full_name,
            e.gender,
            e.date_of_birth,
            e.hire_date,
            e.separation_date,
            COALESCE(e.plant, 'MAIN') AS plant,
            COALESCE(h.department, e.current_department, 'UNKNOWN') AS dept_id,
            COALESCE(h.designation, e.designation, '') AS designation,
            COALESCE(h.grade, e.grade, '') AS grade,
            COALESCE(h.basic_salary, e.basic_salary, 0) AS basic_salary,
            COALESCE(e.employment_type, 'Permanent') AS employment_type,
            CASE WHEN e.separation_date IS NOT NULL THEN 'Separated' ELSE 'Active' END AS employment_status,
            21 AS annual_leave_entitlement,
            COALESCE(h.change_reason, 'HIRE') AS change_reason,
            h.effective_from AS valid_from,
            COALESCE(h.effective_to, e.separation_date, '2099-12-31') AS valid_to,
            CASE WHEN h.effective_to IS NULL OR h.effective_to = '' THEN 1 ELSE 0 END AS is_current
        FROM staging.employees e
        LEFT JOIN staging.employment_history h ON h.emp_id = e.emp_id
        ORDER BY e.emp_id, h.effective_from;
    """)


def load_fact_attendance_daily():
    """Load attendance fact table."""
    print("  loading fact_attendance_daily")
    engine = get_engine()
    
    run_sql_script("""
        INSERT INTO warehouse.fact_attendance_daily (
            employee_sk, date_key, dept_id, shift_code, status, leave_type,
            punch_count, check_in, check_out, scheduled_start, scheduled_end,
            worked_hours, late_minutes, early_minutes, overtime_hours,
            is_sunday, is_holiday
        )
        SELECT
            de.employee_sk,
            substr(replace(ad.work_date, '-', ''), 1, 8) AS date_key,
            COALESCE(de.dept_id, 'UNKNOWN') AS dept_id,
            COALESCE(ad.shift_code, 'GEN') AS shift_code,
            COALESCE(ad.status, 'Absent') AS status,
            NULL AS leave_type,
            COALESCE(ad.punch_count, 0) AS punch_count,
            ad.check_in,
            ad.check_out,
            NULL AS scheduled_start,
            NULL AS scheduled_end,
            COALESCE(ad.worked_hours, 0) AS worked_hours,
            COALESCE(ad.late_minutes, 0) AS late_minutes,
            COALESCE(ad.early_minutes, 0) AS early_minutes,
            COALESCE(ad.overtime_hours, 0) AS overtime_hours,
            COALESCE(dd.is_sunday, 0) AS is_sunday,
            COALESCE(dd.is_holiday, 0) AS is_holiday
        FROM staging.attendance_daily ad
        JOIN warehouse.dim_employee de ON de.emp_id = ad.emp_id
            AND ad.work_date BETWEEN de.valid_from AND de.valid_to
        LEFT JOIN warehouse.dim_date dd ON dd.full_date = ad.work_date
        WHERE ad.work_date IS NOT NULL;
    """)


def load_fact_leave_day():
    """Load leave fact table."""
    print("  loading fact_leave_day")
    engine = get_engine()
    
    run_sql_script("""
        INSERT INTO warehouse.fact_leave_day (
            employee_sk, date_key, dept_id, request_id, leave_type
        )
        SELECT DISTINCT
            de.employee_sk,
            substr(replace(lr.leave_from, '-', ''), 1, 8) AS date_key,
            de.dept_id,
            COALESCE(lr.request_id, '') AS request_id,
            COALESCE(lr.leave_type, 'Annual') AS leave_type
        FROM staging.leave_requests lr
        JOIN warehouse.dim_employee de ON de.emp_id = lr.emp_id
            AND lr.leave_from BETWEEN de.valid_from AND de.valid_to
        WHERE lr.leave_from IS NOT NULL
            AND COALESCE(lr.status, '') = 'Approved';
    """)


def load_fact_overtime_approved():
    """Load overtime approved fact table."""
    print("  loading fact_overtime_approved")
    engine = get_engine()
    
    run_sql_script("""
        INSERT INTO warehouse.fact_overtime_approved (
            request_id, employee_sk, date_key, dept_id, requested_hours, approved_hours
        )
        SELECT
            ot.request_id,
            de.employee_sk,
            COALESCE(substr(replace(ot.request_date, '-', ''), 1, 8), '20260401') AS date_key,
            de.dept_id,
            COALESCE(ot.approved_hours, 0) AS requested_hours,
            COALESCE(ot.approved_hours, 0) AS approved_hours
        FROM staging.overtime_requests ot
        JOIN warehouse.dim_employee de ON de.emp_id = ot.emp_id
            AND ot.request_date BETWEEN de.valid_from AND de.valid_to
        WHERE ot.request_id IS NOT NULL;
    """)


def load_fact_payroll_line():
    """Load payroll fact table."""
    print("  loading fact_payroll_line")
    engine = get_engine()
    
    run_sql_script("""
        INSERT INTO warehouse.fact_payroll_line (
            line_id, employee_sk, date_key, dept_id, payroll_month,
            component, component_type, units, amount
        )
        SELECT
            pl.line_id,
            de.employee_sk,
            (substr(pl.payroll_month, 1, 4) || substr(pl.payroll_month, 6, 2) || '01') AS date_key,
            de.dept_id,
            pl.payroll_month,
            pl.component,
            pl.component_type,
            CAST(pl.units AS REAL) AS units,
            CAST(pl.amount AS REAL) AS amount
        FROM raw.payroll_lines pl
        JOIN staging.employees e ON e.emp_id = pl.emp_id
        JOIN warehouse.dim_employee de ON de.emp_id = e.emp_id
            AND pl.payroll_month BETWEEN substr(de.valid_from, 1, 7) AND substr(de.valid_to, 1, 7);
    """)


def create_views():
    """Views are already created by schema.sql, so this is a no-op."""
    pass
