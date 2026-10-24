-- Q6. Departments where paid overtime exceeds computed overtime by more than 15%.
-- Measured over the six months. Department as of month end (rule 3).
-- excess_pct = (paid - computed) / computed.
WITH emp_month AS (
    SELECT emp_id, month_key, dept_id FROM warehouse.v_employee_month
),
computed AS (
    SELECT em.dept_id, SUM(f.overtime_hours) AS computed_ot_hours
    FROM warehouse.fact_attendance_daily f
    JOIN warehouse.dim_employee de ON de.employee_sk = f.employee_sk
    JOIN warehouse.dim_date dt     ON dt.date_key = f.date_key
    JOIN emp_month em ON em.emp_id = de.emp_id AND em.month_key = substr(dt.full_date, 1, 7)
    WHERE dt.full_date BETWEEN '2026-04-01' AND '2026-09-30'
    GROUP BY em.dept_id
),
paid AS (
    SELECT em.dept_id, SUM(p.units) AS paid_ot_hours
    FROM warehouse.fact_payroll_line p
    JOIN warehouse.dim_employee de ON de.employee_sk = p.employee_sk
    JOIN emp_month em ON em.emp_id = de.emp_id AND em.month_key = p.payroll_month
    WHERE p.component = 'OVERTIME'
    GROUP BY em.dept_id
),
totals AS (
    SELECT dd.plant, dd.dept_name AS department, dd.dept_id,
           ROUND(COALESCE(c.computed_ot_hours, 0), 1) AS computed_ot_hours,
           ROUND(COALESCE(p.paid_ot_hours, 0), 1)     AS paid_ot_hours
    FROM warehouse.dim_department dd
    LEFT JOIN computed c ON c.dept_id = dd.dept_id
    LEFT JOIN paid p     ON p.dept_id = dd.dept_id
)
SELECT plant, department, computed_ot_hours, paid_ot_hours,
       ROUND(paid_ot_hours - computed_ot_hours, 1) AS paid_minus_computed,
       ROUND(100.0 * (paid_ot_hours - computed_ot_hours) / computed_ot_hours, 2) AS excess_pct
FROM totals
WHERE computed_ot_hours > 0
  AND (paid_ot_hours - computed_ot_hours) / computed_ot_hours > 0.15
ORDER BY excess_pct DESC;
