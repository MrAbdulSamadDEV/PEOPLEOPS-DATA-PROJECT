-- Stage 4 - Star schema (SQL DDL)
-- Rebuilt from scratch on every run. Primary and foreign keys are enforced
-- (PRAGMA foreign_keys = ON is set on every connection).

DROP VIEW  IF EXISTS warehouse.v_headcount_month_end;
DROP VIEW  IF EXISTS warehouse.v_employee_month;
DROP VIEW  IF EXISTS warehouse.v_month;
DROP TABLE IF EXISTS warehouse.fact_payroll_line;
DROP TABLE IF EXISTS warehouse.fact_overtime_approved;
DROP TABLE IF EXISTS warehouse.fact_leave_day;
DROP TABLE IF EXISTS warehouse.fact_attendance_daily;
DROP TABLE IF EXISTS warehouse.dim_employee;
DROP TABLE IF EXISTS warehouse.dim_shift;
DROP TABLE IF EXISTS warehouse.dim_department;
DROP TABLE IF EXISTS warehouse.dim_date;
DROP TABLE IF EXISTS warehouse.dq_results;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE warehouse.dim_date (
    date_key      INTEGER PRIMARY KEY,                      -- yyyymmdd
    full_date     TEXT    NOT NULL UNIQUE,                  -- YYYY-MM-DD
    year          INTEGER NOT NULL,
    month_number  INTEGER NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    month_key     TEXT    NOT NULL,                         -- YYYY-MM
    month_start   TEXT    NOT NULL,
    month_end     TEXT    NOT NULL,
    day_of_week   INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),  -- 0 = Sunday
    is_sunday     INTEGER NOT NULL CHECK (is_sunday IN (0, 1)),
    is_month_end  INTEGER NOT NULL CHECK (is_month_end IN (0, 1))
);

CREATE TABLE warehouse.dim_department (
    dept_id        TEXT PRIMARY KEY,
    dept_name      TEXT NOT NULL,
    plant          TEXT NOT NULL,
    cost_center    TEXT NOT NULL UNIQUE,
    previous_name  TEXT,
    renamed_on     TEXT
);

CREATE TABLE warehouse.dim_shift (
    shift_code       TEXT PRIMARY KEY,
    shift_name       TEXT    NOT NULL,
    start_time       TEXT    NOT NULL,
    end_time         TEXT    NOT NULL,
    crosses_midnight INTEGER NOT NULL CHECK (crosses_midnight IN (0, 1)),
    grace_minutes    INTEGER NOT NULL
);

-- SCD Type 2: one row per employee per employment version (rule 2).
-- Personal contact fields (email, phone) are not loaded: not needed for the analysis.
CREATE TABLE warehouse.dim_employee (
    employee_sk              INTEGER PRIMARY KEY,
    emp_id                   TEXT    NOT NULL,
    full_name                TEXT    NOT NULL,
    gender                   TEXT,
    date_of_birth            TEXT,
    hire_date                TEXT    NOT NULL,
    separation_date          TEXT,
    plant                    TEXT    NOT NULL,
    dept_id                  TEXT    NOT NULL REFERENCES dim_department (dept_id),
    designation              TEXT,
    grade                    TEXT,
    basic_salary             REAL,
    employment_type          TEXT,
    employment_status        TEXT    NOT NULL CHECK (employment_status IN ('Active', 'Separated')),
    annual_leave_entitlement INTEGER NOT NULL,
    change_reason            TEXT    NOT NULL,
    valid_from               TEXT    NOT NULL,
    valid_to                 TEXT    NOT NULL,
    is_current               INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    UNIQUE (emp_id, valid_from),
    CHECK (valid_from <= valid_to)
);

-- ------------------------------------------------------------------- facts
CREATE TABLE warehouse.fact_attendance_daily (
    attendance_key   INTEGER PRIMARY KEY,
    employee_sk      INTEGER NOT NULL REFERENCES dim_employee (employee_sk),
    date_key         INTEGER NOT NULL REFERENCES dim_date (date_key),
    dept_id          TEXT    NOT NULL REFERENCES dim_department (dept_id),
    shift_code       TEXT    REFERENCES dim_shift (shift_code),
    status           TEXT    NOT NULL CHECK (status IN
                         ('Present', 'Absent', 'On Leave', 'Holiday', 'Weekly Off', 'Missing Punch')),
    leave_type       TEXT    CHECK (leave_type IN ('Annual', 'Casual', 'Sick')),
    punch_count      INTEGER NOT NULL CHECK (punch_count >= 0),
    check_in         TEXT,
    check_out        TEXT,
    scheduled_start  TEXT,
    scheduled_end    TEXT,
    worked_hours     REAL    NOT NULL CHECK (worked_hours >= 0),
    late_minutes     REAL    NOT NULL CHECK (late_minutes >= 0),
    early_minutes    REAL    NOT NULL CHECK (early_minutes >= 0),
    overtime_hours   REAL    NOT NULL CHECK (overtime_hours >= 0),
    is_sunday        INTEGER NOT NULL CHECK (is_sunday IN (0, 1)),
    is_holiday       INTEGER NOT NULL CHECK (is_holiday IN (0, 1)),
    UNIQUE (employee_sk, date_key)
);

CREATE TABLE warehouse.fact_leave_day (
    leave_day_key  INTEGER PRIMARY KEY,
    employee_sk    INTEGER NOT NULL REFERENCES dim_employee (employee_sk),
    date_key       INTEGER NOT NULL REFERENCES dim_date (date_key),
    dept_id        TEXT    NOT NULL REFERENCES dim_department (dept_id),
    request_id     TEXT    NOT NULL,
    leave_type     TEXT    NOT NULL CHECK (leave_type IN ('Annual', 'Casual', 'Sick')),
    UNIQUE (employee_sk, date_key)
);

CREATE TABLE warehouse.fact_overtime_approved (
    request_id       TEXT PRIMARY KEY,
    employee_sk      INTEGER NOT NULL REFERENCES dim_employee (employee_sk),
    date_key         INTEGER NOT NULL REFERENCES dim_date (date_key),
    dept_id          TEXT    NOT NULL REFERENCES dim_department (dept_id),
    requested_hours  REAL    NOT NULL CHECK (requested_hours >= 0),
    approved_hours   REAL    NOT NULL CHECK (approved_hours >= 0),
    approver_id      TEXT
);

CREATE TABLE warehouse.fact_payroll_line (
    line_id          TEXT PRIMARY KEY,
    employee_sk      INTEGER NOT NULL REFERENCES dim_employee (employee_sk),
    date_key         INTEGER NOT NULL REFERENCES dim_date (date_key),   -- reference date (rule 3)
    dept_id          TEXT    NOT NULL REFERENCES dim_department (dept_id),
    payroll_month    TEXT    NOT NULL,
    component        TEXT    NOT NULL CHECK (component IN
                         ('BASIC', 'HOUSE_RENT', 'MEDICAL', 'CONVEYANCE', 'OVERTIME',
                          'INCOME_TAX', 'EOBI', 'ABSENCE_DEDUCTION', 'LOAN_INSTALLMENT')),
    component_type   TEXT    NOT NULL CHECK (component_type IN ('EARNING', 'DEDUCTION')),
    units            REAL,
    amount           REAL    NOT NULL
);

CREATE INDEX warehouse.ix_att_date ON fact_attendance_daily (date_key);
CREATE INDEX warehouse.ix_pay_month ON fact_payroll_line (payroll_month);
-- Reusable views that encode the reporting rules once, so every answer uses them.

-- The six reporting months of the period, plus March for opening headcount.
CREATE VIEW warehouse.v_month AS
SELECT DISTINCT month_key, month_start, month_end
FROM warehouse.dim_date
WHERE month_key BETWEEN '2026-03' AND '2026-09';

-- Rule 3: the department an employee belongs to for a month is the one they
-- were in on the last day of the month, or on their last working day if they
-- left during that month. Only months in which the employee was employed.
CREATE VIEW warehouse.v_employee_month AS
WITH emp AS (
    SELECT emp_id,
           MIN(hire_date)        AS hire_date,
           MAX(separation_date)  AS separation_date
    FROM warehouse.dim_employee
    GROUP BY emp_id
),
em AS (
    SELECT m.month_key,
           m.month_start,
           m.month_end,
           e.emp_id,
           MIN(m.month_end, COALESCE(e.separation_date, m.month_end)) AS reference_date
    FROM warehouse.v_month m
    CROSS JOIN emp e
    WHERE e.hire_date <= m.month_end
      AND (e.separation_date IS NULL OR e.separation_date >= m.month_start)
)
SELECT em.month_key,
       em.emp_id,
       em.reference_date,
       d.employee_sk,
       d.dept_id,
       d.plant
FROM em
JOIN warehouse.dim_employee d
  ON d.emp_id = em.emp_id
 AND em.reference_date BETWEEN d.valid_from AND d.valid_to;

-- Rule 4: head count at month end (hired on or before month end, and not
-- separated on or before month end). Department as of month end (rule 3).
CREATE VIEW warehouse.v_headcount_month_end AS
SELECT m.month_key,
       d.plant,
       d.dept_id,
       COUNT(DISTINCT d.emp_id) AS headcount
FROM warehouse.v_month m
JOIN warehouse.dim_employee d
  ON m.month_end BETWEEN d.valid_from AND d.valid_to
WHERE d.hire_date <= m.month_end
  AND (d.separation_date IS NULL OR d.separation_date > m.month_end)
GROUP BY m.month_key, d.plant, d.dept_id;
