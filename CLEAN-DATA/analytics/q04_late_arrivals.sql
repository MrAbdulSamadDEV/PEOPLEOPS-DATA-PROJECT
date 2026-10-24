-- Q4. The 10 employees with the most late arrivals, with their department.
-- Late = check-in more than 10 minutes after shift start, on a Present working
-- day (rule 13). Department = the one on the employee's last working day in the
-- period (rule 3). Ties broken by total late minutes, then emp_id.
WITH last_month AS (
    SELECT vem.*,
           ROW_NUMBER() OVER (PARTITION BY vem.emp_id ORDER BY vem.month_key DESC) AS rn
    FROM warehouse.v_employee_month vem
),
late AS (
    SELECT de.emp_id,
           COUNT(*)                    AS late_arrivals,
           ROUND(SUM(f.late_minutes), 1) AS total_late_minutes
    FROM warehouse.fact_attendance_daily f
    JOIN warehouse.dim_employee de ON de.employee_sk = f.employee_sk
    JOIN warehouse.dim_date dt     ON dt.date_key = f.date_key
    WHERE f.late_minutes > 0
      AND dt.full_date BETWEEN '2026-04-01' AND '2026-09-30'
    GROUP BY de.emp_id
)
SELECT l.emp_id,
       (SELECT full_name FROM warehouse.dim_employee d WHERE d.emp_id = l.emp_id LIMIT 1) AS full_name,
       dd.dept_name AS department,
       l.late_arrivals,
       l.total_late_minutes
FROM late l
JOIN last_month lm ON lm.emp_id = l.emp_id AND lm.rn = 1
JOIN warehouse.dim_department dd ON dd.dept_id = lm.dept_id
ORDER BY l.late_arrivals DESC, l.total_late_minutes DESC, l.emp_id
LIMIT 10;
