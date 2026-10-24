-- Q7. Employees paid in a month with zero attendance in that month.
-- Attendance = Present or Missing Punch days (rule 12). Paid = gross earnings > 0
-- (EARNING lines, rule 21). Department as of the reference date (rule 3).
WITH pay AS (
    SELECT de.emp_id,
           de.full_name,
           p.payroll_month AS month_key,
           p.dept_id,
           ROUND(SUM(CASE WHEN p.component_type = 'EARNING' THEN p.amount ELSE 0 END), 2) AS gross_earnings
    FROM warehouse.fact_payroll_line p
    JOIN warehouse.dim_employee de ON de.employee_sk = p.employee_sk
    GROUP BY de.emp_id, de.full_name, p.payroll_month, p.dept_id
),
att AS (
    SELECT de.emp_id,
           substr(dt.full_date, 1, 7) AS month_key,
           SUM(CASE WHEN f.status IN ('Present', 'Missing Punch') THEN 1 ELSE 0 END) AS attended_days,
           SUM(CASE WHEN f.status = 'On Leave' THEN 1 ELSE 0 END) AS leave_days
    FROM warehouse.fact_attendance_daily f
    JOIN warehouse.dim_employee de ON de.employee_sk = f.employee_sk
    JOIN warehouse.dim_date dt     ON dt.date_key = f.date_key
    GROUP BY de.emp_id, substr(dt.full_date, 1, 7)
)
SELECT p.emp_id,
       p.full_name,
       dd.dept_name AS department,
       p.month_key  AS month,
       p.gross_earnings,
       COALESCE(a.attended_days, 0) AS attended_days,
       COALESCE(a.leave_days, 0)    AS on_leave_days
FROM pay p
LEFT JOIN att a ON a.emp_id = p.emp_id AND a.month_key = p.month_key
JOIN warehouse.dim_department dd ON dd.dept_id = p.dept_id
WHERE COALESCE(a.attended_days, 0) = 0
  AND p.gross_earnings > 0
  AND p.month_key BETWEEN '2026-04' AND '2026-09'
ORDER BY p.month_key, dd.dept_name, p.emp_id;
