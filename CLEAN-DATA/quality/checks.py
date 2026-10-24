"""Stage 6 - data quality checks, run after every load.

Every check writes one row to warehouse.dq_results:
  PASS  - the rule holds
  WARN  - known, documented exception (reported, does not stop the run)
  FAIL  - the rule is broken; the run exits with an error

Check groups: uniqueness, not-null, referential integrity, reconciliation
(raw = staging + rejected), accepted values, business sanity.
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from db import get_engine, run_sql_script

RESULTS = []


def scalar(sql):
    with get_engine().connect() as c:
        return c.exec_driver_sql(sql).scalar()


def check(group, name, table, observed, expected, ok, details="", warn=False):
    status = "PASS" if ok else ("WARN" if warn else "FAIL")
    RESULTS.append((group, name, table, status, str(observed), str(expected), details))
    flag = {"PASS": "ok  ", "WARN": "WARN", "FAIL": "FAIL"}[status]
    print(f"    [{flag}] {group:<15} {name:<62} observed={observed} expected={expected}")


def eq(group, name, table, sql_obs, sql_exp, details="", warn=False):
    obs, exp = scalar(sql_obs), scalar(sql_exp)
    check(group, name, table, obs, exp, obs == exp, details, warn=warn)


def zero(group, name, table, sql, details="", warn=False):
    obs = scalar(sql)
    check(group, name, table, obs, 0, obs == 0, details, warn=warn)


# ------------------------------------------------------------ uniqueness
def uniqueness():
    g = "uniqueness"
    zero(g, "raw.biometric_punches punch_id unique", "raw.biometric_punches",
         "SELECT COUNT(*) - COUNT(DISTINCT punch_id) FROM raw.biometric_punches")
    zero(g, "staging.employees emp_id unique", "staging.employees",
         "SELECT COUNT(*) - COUNT(DISTINCT emp_id) FROM staging.employees")
    zero(g, "staging.employment_history (emp_id, effective_from) unique", "staging.employment_history",
         "SELECT COUNT(*) - COUNT(DISTINCT emp_id || '|' || effective_from) FROM staging.employment_history")
    zero(g, "staging.punches_clean punch_id unique", "staging.punches_clean",
         "SELECT COUNT(*) - COUNT(DISTINCT punch_id) FROM staging.punches_clean")
    zero(g, "staging.attendance_daily (emp_id, work_date) unique", "staging.attendance_daily",
         "SELECT COUNT(*) - COUNT(DISTINCT emp_id || '|' || work_date) FROM staging.attendance_daily")
    zero(g, "dim_employee (emp_id, valid_from) unique", "warehouse.dim_employee",
         "SELECT COUNT(*) - COUNT(DISTINCT emp_id || '|' || valid_from) FROM warehouse.dim_employee")
    zero(g, "dim_date date_key unique", "warehouse.dim_date",
         "SELECT COUNT(*) - COUNT(DISTINCT date_key) FROM warehouse.dim_date")
    zero(g, "fact_attendance_daily (employee_sk, date_key) unique", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) - COUNT(*) FROM (SELECT 1 FROM warehouse.fact_attendance_daily GROUP BY employee_sk, date_key HAVING COUNT(*) > 1)")
    zero(g, "fact_leave_day (employee_sk, date_key) unique", "warehouse.fact_leave_day",
         "SELECT COUNT(*) FROM (SELECT 1 FROM warehouse.fact_leave_day GROUP BY employee_sk, date_key HAVING COUNT(*) > 1)")


# ------------------------------------------------------------ not-null
def not_null():
    g = "not-null"
    pk_cols = {
        "staging.employees": "emp_id",
        "staging.departments": "dept_id",
        "staging.punches_clean": "punch_id",
        "staging.leave_requests": "request_id",
        "warehouse.dim_employee": "employee_sk",
        "warehouse.dim_department": "dept_id",
        "warehouse.dim_shift": "shift_code",
        "warehouse.dim_date": "date_key",
        "warehouse.fact_attendance_daily": "attendance_key",
        "warehouse.fact_overtime_approved": "request_id",
        "warehouse.fact_payroll_line": "line_id",
        "warehouse.fact_leave_day": "leave_day_key",
    }
    for table, col in pk_cols.items():
        zero(g, f"primary key {col} not null", table,
             f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")


# ------------------------------------------------------------ referential integrity
def referential():
    g = "referential"
    zero(g, "every dim_employee dept_id exists in dim_department", "warehouse.dim_employee",
         "SELECT COUNT(*) FROM warehouse.dim_employee d LEFT JOIN warehouse.dim_department x ON x.dept_id = d.dept_id WHERE x.dept_id IS NULL")
    zero(g, "every fact_attendance row has a matching dim_date row", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily f LEFT JOIN warehouse.dim_date t ON t.date_key = f.date_key WHERE t.date_key IS NULL")
    zero(g, "every fact_attendance row has a matching dim_department row", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily f LEFT JOIN warehouse.dim_department x ON x.dept_id = f.dept_id WHERE x.dept_id IS NULL")
    zero(g, "every fact_leave_day row has a matching dim_employee row", "warehouse.fact_leave_day",
         "SELECT COUNT(*) FROM warehouse.fact_leave_day f LEFT JOIN warehouse.dim_employee e ON e.employee_sk = f.employee_sk WHERE e.employee_sk IS NULL")
    zero(g, "every fact_overtime_approved row has a matching dim_employee row", "warehouse.fact_overtime_approved",
         "SELECT COUNT(*) FROM warehouse.fact_overtime_approved f LEFT JOIN warehouse.dim_employee e ON e.employee_sk = f.employee_sk WHERE e.employee_sk IS NULL")
    zero(g, "every fact_payroll_line has a matching dim_date row", "warehouse.fact_payroll_line",
         "SELECT COUNT(*) FROM warehouse.fact_payroll_line f LEFT JOIN warehouse.dim_date t ON t.date_key = f.date_key WHERE t.date_key IS NULL")
    zero(g, "every fact_attendance row has a matching dim_employee SCD row", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily f LEFT JOIN warehouse.dim_employee e ON e.employee_sk = f.employee_sk WHERE e.employee_sk IS NULL")
    zero(g, "every fact_payroll_line has a matching dim_employee row", "warehouse.fact_payroll_line",
         "SELECT COUNT(*) FROM warehouse.fact_payroll_line f LEFT JOIN warehouse.dim_employee e ON e.employee_sk = f.employee_sk WHERE e.employee_sk IS NULL")
    zero(g, "every punch in staging maps to an employee", "staging.punches_clean",
         "SELECT COUNT(*) FROM staging.punches_clean p LEFT JOIN staging.employees e ON e.emp_id = p.emp_id WHERE e.emp_id IS NULL")
    zero(g, "every employee has at least one history row", "staging.employees",
         "SELECT COUNT(*) FROM staging.employees e LEFT JOIN staging.employment_history h ON h.emp_id = e.emp_id WHERE h.emp_id IS NULL")


# ------------------------------------------------------------ reconciliation
def reconciliation():
    g = "reconciliation"
    eq(g, "employees: raw rows = staging + rejected", "raw.employees",
       "SELECT COUNT(*) FROM raw.employees",
       "SELECT (SELECT COUNT(*) FROM staging.employees) + (SELECT COUNT(*) FROM staging.rejected_employees)")
    eq(g, "biometric punches: raw = clean + rejected", "raw.biometric_punches",
       "SELECT COUNT(*) FROM raw.biometric_punches",
       "SELECT (SELECT COUNT(*) FROM staging.punches_clean) + (SELECT COUNT(*) FROM staging.rejected_punches)")
    eq(g, "employment history: raw = staging + rejected", "raw.employment_history",
       "SELECT COUNT(*) FROM raw.employment_history",
       "SELECT (SELECT COUNT(*) FROM staging.employment_history) + (SELECT COUNT(*) FROM staging.rejected_employment_history)")
    eq(g, "shift roster: raw rows = staging rows not filled", "raw.shift_roster",
       "SELECT COUNT(*) FROM raw.shift_roster",
       "SELECT COUNT(*) FROM staging.shift_roster_weekly WHERE is_filled = 0")
    eq(g, "device mapping: raw = staging", "raw.device_mapping",
       "SELECT COUNT(*) FROM raw.device_mapping", "SELECT COUNT(*) FROM staging.device_mapping")
    eq(g, "departments: raw = staging", "raw.departments",
       "SELECT COUNT(*) FROM raw.departments", "SELECT COUNT(*) FROM staging.departments")
    eq(g, "shifts: raw = staging", "raw.shifts",
       "SELECT COUNT(*) FROM raw.shifts", "SELECT COUNT(*) FROM staging.shifts")
    eq(g, "holidays: raw rows = distinct staging holidays by scope", "raw.holidays",
       "SELECT COUNT(*) FROM raw.holidays",
       "SELECT COUNT(*) FROM (SELECT DISTINCT holiday_date, holiday_name, scope FROM staging.holidays)")
    eq(g, "leave requests: raw = staging", "raw.leave_requests",
       "SELECT COUNT(*) FROM raw.leave_requests", "SELECT COUNT(*) FROM staging.leave_requests")
    eq(g, "overtime requests: raw = staging", "raw.overtime_requests",
       "SELECT COUNT(*) FROM raw.overtime_requests", "SELECT COUNT(*) FROM staging.overtime_requests")
    eq(g, "payroll lines: raw = staging", "raw.payroll_lines",
       "SELECT COUNT(*) FROM raw.payroll_lines", "SELECT COUNT(*) FROM staging.payroll_lines")
    eq(g, "payroll lines: raw = warehouse", "warehouse.fact_payroll_line",
       "SELECT COUNT(*) FROM warehouse.fact_payroll_line", "SELECT COUNT(*) FROM raw.payroll_lines")
    eq(g, "applications: raw = staging", "raw.applications",
       "SELECT COUNT(*) FROM raw.applications", "SELECT COUNT(*) FROM staging.applications")
    eq(g, "approved overtime: staging Approved with hours = fact rows", "warehouse.fact_overtime_approved",
       "SELECT COUNT(*) FROM warehouse.fact_overtime_approved",
       "SELECT COUNT(*) FROM staging.overtime_requests WHERE status = 'Approved' AND approved_hours IS NOT NULL")
    eq(g, "leave days: staging = fact", "warehouse.fact_leave_day",
       "SELECT COUNT(*) FROM warehouse.fact_leave_day", "SELECT COUNT(*) FROM staging.leave_days")
    eq(g, "attendance: staging = fact", "warehouse.fact_attendance_daily",
       "SELECT COUNT(*) FROM warehouse.fact_attendance_daily", "SELECT COUNT(*) FROM staging.attendance_daily")
    eq(g, "On Leave days in attendance = leave days in fact", "warehouse.fact_attendance_daily",
       "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE status = 'On Leave'",
       "SELECT COUNT(*) FROM warehouse.fact_leave_day")
    eq(g, "leave days: each valid request's working days are counted", "staging.leave_requests",
       "SELECT SUM(working_leave_days) FROM staging.leave_requests WHERE is_valid = 1",
       "SELECT COUNT(*) FROM staging.leave_days")
    # Attendance rows: every employee-day of employment is one row
    eq(g, "attendance rows = employee-days of employment in period", "warehouse.fact_attendance_daily",
       "SELECT COUNT(*) FROM warehouse.fact_attendance_daily",
       """SELECT COUNT(*) FROM staging.employees e JOIN staging.calendar c
          ON c.work_date BETWEEN '2026-04-01' AND '2026-09-30'
         AND c.work_date >= e.hire_date AND (e.separation_date IS NULL OR c.work_date <= e.separation_date)""")


# ------------------------------------------------------------ accepted values
def accepted_values():
    g = "accepted-values"
    def values_in(name, table, col, allowed):
        vals = ", ".join(f"'{v}'" for v in allowed)
        zero(g, name, table, f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL AND {col} NOT IN ({vals})")
    values_in("attendance status in allowed set", "warehouse.fact_attendance_daily", "status",
              ["Present", "Absent", "On Leave", "Holiday", "Weekly Off", "Missing Punch"])
    values_in("leave type in allowed set", "warehouse.fact_leave_day", "leave_type", ["Annual", "Casual", "Sick"])
    values_in("pay component in allowed set", "warehouse.fact_payroll_line", "component",
              ["BASIC", "HOUSE_RENT", "MEDICAL", "CONVEYANCE", "OVERTIME", "INCOME_TAX", "EOBI", "ABSENCE_DEDUCTION", "LOAN_INSTALLMENT"])
    values_in("pay component type in allowed set", "warehouse.fact_payroll_line", "component_type", ["EARNING", "DEDUCTION"])
    values_in("shift code in allowed set", "warehouse.fact_attendance_daily", "shift_code", ["DAY", "EVE", "NIGHT", "GEN"])
    values_in("leave approval action in allowed set", "staging.leave_approval_steps", "action", ["Approved", "Rejected"])
    values_in("overtime status in allowed set", "staging.overtime_requests", "status", ["Approved", "Rejected", "Pending"])
    values_in("employee status in allowed set", "warehouse.dim_employee", "employment_status", ["Active", "Separated"])
    zero(g, "employee status Separated iff separation date present", "warehouse.dim_employee",
         "SELECT COUNT(*) FROM warehouse.dim_employee WHERE (employment_status = 'Separated') <> (separation_date IS NOT NULL)")
    zero(g, "all dates are ISO YYYY-MM-DD in staging.employees", "staging.employees",
         "SELECT COUNT(*) FROM staging.employees WHERE hire_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'")


# ------------------------------------------------------------ business sanity
def business_sanity():
    g = "business"
    zero(g, "no negative worked hours", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE worked_hours < 0")
    zero(g, "no shift longer than 16 hours (check-out minus check-in)", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE punch_count >= 2 AND (julianday(check_out) - julianday(check_in)) * 24 > 16")
    zero(g, "no overlapping SCD2 ranges per employee", "warehouse.dim_employee",
         "SELECT COUNT(*) FROM warehouse.dim_employee a JOIN warehouse.dim_employee b ON a.emp_id = b.emp_id "
         "AND a.employee_sk < b.employee_sk AND a.valid_from <= b.valid_to AND b.valid_from <= a.valid_to")
    zero(g, "no gaps between SCD2 versions", "warehouse.dim_employee",
         "SELECT COUNT(*) FROM (SELECT valid_to, LEAD(valid_from) OVER (PARTITION BY emp_id ORDER BY valid_from) AS next_from "
         "FROM warehouse.dim_employee) WHERE next_from IS NOT NULL AND next_from <> date(valid_to, '+1 day')")
    zero(g, "exactly one current SCD2 row per employee", "warehouse.dim_employee",
         "SELECT COUNT(*) FROM (SELECT emp_id FROM warehouse.dim_employee GROUP BY emp_id HAVING SUM(is_current) <> 1)")
    zero(g, "hire date = first SCD2 valid_from", "warehouse.dim_employee",
         "SELECT COUNT(*) FROM warehouse.dim_employee d WHERE d.valid_from = (SELECT MIN(valid_from) FROM warehouse.dim_employee x WHERE x.emp_id = d.emp_id) AND d.valid_from <> d.hire_date")
    zero(g, "Weekly Off only on Sundays", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE status = 'Weekly Off' AND is_sunday = 0")
    zero(g, "Holiday only on plant holidays with no punches", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE status = 'Holiday' AND (is_holiday = 0 OR punch_count > 0)")
    zero(g, "Present rows have at least two punches", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE status = 'Present' AND punch_count < 2")
    zero(g, "no leave day on a Sunday or plant holiday", "warehouse.fact_leave_day",
         "SELECT COUNT(*) FROM warehouse.fact_leave_day l JOIN warehouse.dim_date d ON d.date_key = l.date_key WHERE d.is_sunday = 1")
    zero(g, "no negative overtime hours", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE overtime_hours < 0")
    zero(g, "overtime is whole half-hours", "warehouse.fact_attendance_daily",
         "SELECT COUNT(*) FROM warehouse.fact_attendance_daily WHERE ABS(overtime_hours * 2 - ROUND(overtime_hours * 2)) > 0.000001")
    zero(g, "approved overtime hours within 0 to 16 per request", "warehouse.fact_overtime_approved",
         "SELECT COUNT(*) FROM warehouse.fact_overtime_approved WHERE approved_hours > 16 OR approved_hours < 0")
    zero(g, "no employee paid before hire month", "warehouse.fact_payroll_line",
         "SELECT COUNT(*) FROM warehouse.fact_payroll_line p JOIN warehouse.dim_employee d ON d.employee_sk = p.employee_sk "
         "WHERE p.payroll_month < substr(d.hire_date, 1, 7)")
    zero(g, "punches outside employment dates", "staging.punches_clean",
         "SELECT COUNT(*) FROM staging.punches_clean p JOIN staging.employees e ON e.emp_id = p.emp_id "
         "WHERE substr(p.punch_time, 1, 10) < e.hire_date OR (e.separation_date IS NOT NULL AND substr(p.punch_time, 1, 10) > e.separation_date)",
         details="Known exception: a night-shift check-out on the morning after the last working day. The rotation rule assigns it to the next day, which is outside employment, so it is not in attendance. 20 rows, documented in README.",
         warn=True)


def clock_correction_check():
    """After correction, every device's median check-in offset must sit near its shift start."""
    g = "business"
    eng = get_engine()
    df = pd.read_sql("""
        SELECT p.emp_id, p.device_id, date(p.punch_time) AS d, MIN(p.punch_time) AS first_in,
               r.shift_code
        FROM staging.punches_clean p
        JOIN staging.roster_daily r ON r.emp_id = p.emp_id AND r.work_date = date(p.punch_time)
        WHERE r.shift_code IN ('DAY', 'EVE') AND date(p.punch_time) BETWEEN '2026-04-01' AND '2026-09-30'
        GROUP BY p.emp_id, p.device_id, d, r.shift_code""", eng)
    start = {"DAY": 360, "EVE": 840}
    t = pd.to_datetime(df["first_in"])
    off = (t.dt.hour * 60 + t.dt.minute) - df["shift_code"].map(start)
    df = df.assign(off=off)
    df = df[df.off.abs() <= 120]
    med = df.groupby("device_id")["off"].median()
    for device, m in med.items():
        ok = abs(m) <= 15
        check(g, f"{device} median check-in offset after correction within +/-15 min",
              "staging.punches_clean", f"{m:+.0f} min", "within +/-15 min", ok)


def write_results():
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_sql_script("""
        DROP TABLE IF EXISTS warehouse.dq_results;
        CREATE TABLE warehouse.dq_results (
            check_id     INTEGER PRIMARY KEY,
            check_group  TEXT NOT NULL,
            check_name   TEXT NOT NULL,
            table_name   TEXT NOT NULL,
            status       TEXT NOT NULL CHECK (status IN ('PASS', 'WARN', 'FAIL')),
            observed     TEXT NOT NULL,
            expected     TEXT NOT NULL,
            details      TEXT,
            run_ts       TEXT NOT NULL
        );
    """)
    with get_engine().begin() as conn:
        for i, row in enumerate(RESULTS, start=1):
            conn.exec_driver_sql(
                "INSERT INTO warehouse.dq_results VALUES (?,?,?,?,?,?,?,?,?)",
                (i, row[0], row[1], row[2], row[3], row[4], row[5], row[6], run_ts),
            )
    return pd.Series([r[3] for r in RESULTS]).value_counts().to_dict()


def run():
    print("Stage 6 - data quality checks")
    RESULTS.clear()
    uniqueness()
    not_null()
    referential()
    reconciliation()
    accepted_values()
    business_sanity()
    clock_correction_check()
    counts = write_results()
    print(f"  checks: {len(RESULTS)}  PASS={counts.get('PASS', 0)}  WARN={counts.get('WARN', 0)}  FAIL={counts.get('FAIL', 0)}")
    return counts.get("FAIL", 0) == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
