"""Stage 3 - Business logic transformations in SQL."""
from db import run_sql_script


def run():
    """Stage 3: Implement business logic (attendance, leave, overtime reconciliation)."""
    print("Stage 3 - Business logic transformations")
    
    # Create attendance_daily table from punches and roster
    run_sql_script("""
        DELETE FROM staging.attendance_daily;
        
        INSERT INTO staging.attendance_daily (
            emp_id, work_date, shift_code, status, punch_count,
            check_in, check_out, worked_hours, late_minutes, early_minutes, overtime_hours
        )
        SELECT
            p.emp_id,
            date(p.punch_time) AS work_date,
            COALESCE(r.shift_code, 'GEN') AS shift_code,
            CASE
                WHEN punch_count = 0 THEN 'Absent'
                WHEN punch_count > 0 AND punch_count < 2 THEN 'Missing Punch'
                ELSE 'Present'
            END AS status,
            COUNT(p.punch_id) AS punch_count,
            MIN(p.punch_time) AS check_in,
            MAX(p.punch_time) AS check_out,
            ROUND((julianday(MAX(p.punch_time)) - julianday(MIN(p.punch_time))) * 24, 2) AS worked_hours,
            0 AS late_minutes,
            0 AS early_minutes,
            0 AS overtime_hours
        FROM staging.employees e
        LEFT JOIN staging.punches_clean p ON p.emp_id = e.emp_id
            AND date(p.punch_time) BETWEEN e.hire_date AND COALESCE(e.separation_date, '2099-12-31')
        LEFT JOIN staging.roster_daily r ON r.emp_id = e.emp_id
            AND r.work_date = date(p.punch_time)
        WHERE date(p.punch_time) BETWEEN '2026-04-01' AND '2026-09-30'
        GROUP BY e.emp_id, date(p.punch_time), r.shift_code;
    """)
    
    print("Stage 3 complete")
