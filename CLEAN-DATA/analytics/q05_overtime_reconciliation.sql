-- Q5. Overtime hours by department and month: computed from punches, approved
-- (overtime requests with status Approved), and paid (payroll OVERTIME units).
-- Department as of the month end (rule 3); payroll month is the reporting month.
WITH emp_month AS (
    SELECT emp_id, month_key, dept_id FROM warehouse.v_employee_month
),
computed AS (
    SELECT em.month_key, em.dept_id, SUM(f.overtime_hours) AS computed_ot_hours
    FROM warehouse.fact_attendance_daily f
    JOIN warehouse.dim_employee de ON de.employee_sk = f.employee_sk
    JOIN warehouse.dim_date dt     ON dt.date_key = f.date_key
    JOIN emp_month em ON em.emp_id = de.emp_id AND em.month_key = substr(dt.full_date, 1, 7)
    WHERE dt.full_date BETWEEN '2026-04-01' AND '2026-09-30'
    GROUP BY em.month_key, em.dept_id
),
approved AS (
    SELECT em.month_key, em.dept_id, SUM(o.approved_hours) AS approved_ot_hours
    FROM warehouse.fact_overtime_approved o
    JOIN warehouse.dim_employee de ON de.employee_sk = o.employee_sk
    JOIN warehouse.dim_date dt     ON dt.date_key = o.date_key
    JOIN emp_month em ON em.emp_id = de.emp_id AND em.month_key = substr(dt.full_date, 1, 7)
    WHERE dt.full_date BETWEEN '2026-04-01' AND '2026-09-30'
    GROUP BY em.month_key, em.dept_id
),
paid AS (
    SELECT em.month_key, em.dept_id, SUM(p.units) AS paid_ot_hours
    FROM warehouse.fact_payroll_line p
    JOIN warehouse.dim_employee de ON de.employee_sk = p.employee_sk
    JOIN emp_month em ON em.emp_id = de.emp_id AND em.month_key = p.payroll_month
    WHERE p.component = 'OVERTIME'
    GROUP BY em.month_key, em.dept_id
),
keys AS (
    SELECT month_key, dept_id FROM computed
    UNION SELECT month_key, dept_id FROM approved
    UNION SELECT month_key, dept_id FROM paid
)
SELECT k.month_key AS month,
       dd.plant,
       dd.dept_name AS department,
       ROUND(COALESCE(c.computed_ot_hours, 0), 1) AS computed_ot_hours,
       ROUND(COALESCE(a.approved_ot_hours, 0), 1) AS approved_ot_hours,
       ROUND(COALESCE(p.paid_ot_hours, 0), 1)     AS paid_ot_hours,
       ROUND(COALESCE(p.paid_ot_hours, 0) - COALESCE(c.computed_ot_hours, 0), 1) AS paid_minus_computed
FROM keys k
JOIN warehouse.dim_department dd ON dd.dept_id = k.dept_id
LEFT JOIN computed c ON c.month_key = k.month_key AND c.dept_id = k.dept_id
LEFT JOIN approved a ON a.month_key = k.month_key AND a.dept_id = k.dept_id
LEFT JOIN paid p     ON p.month_key = k.month_key AND p.dept_id = k.dept_id
ORDER BY k.month_key, dd.plant, dd.dept_name;
