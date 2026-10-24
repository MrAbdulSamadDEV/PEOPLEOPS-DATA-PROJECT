-- Q10. Employees whose approved Annual leave days in these six months already
-- exceed their full-year Annual entitlement (rules 16-18).
-- Leave days are counted once per calendar day, Sundays and holidays excluded.
WITH annual AS (
    SELECT de.emp_id,
           COUNT(*) AS annual_leave_days
    FROM warehouse.fact_leave_day l
    JOIN warehouse.dim_employee de ON de.employee_sk = l.employee_sk
    JOIN warehouse.dim_date dt     ON dt.date_key = l.date_key
    WHERE l.leave_type = 'Annual'
      AND dt.full_date BETWEEN '2026-04-01' AND '2026-09-30'
    GROUP BY de.emp_id
),
latest AS (
    SELECT vem.emp_id, vem.dept_id,
           ROW_NUMBER() OVER (PARTITION BY vem.emp_id ORDER BY vem.month_key DESC) AS rn
    FROM warehouse.v_employee_month vem
)
SELECT d.emp_id,
       d.full_name,
       dd.dept_name AS department,
       d.annual_leave_entitlement,
       a.annual_leave_days,
       a.annual_leave_days - d.annual_leave_entitlement AS days_over_entitlement
FROM annual a
JOIN (SELECT * FROM warehouse.dim_employee WHERE is_current = 1) d ON d.emp_id = a.emp_id
JOIN latest lt ON lt.emp_id = a.emp_id AND lt.rn = 1
JOIN warehouse.dim_department dd ON dd.dept_id = lt.dept_id
WHERE a.annual_leave_days > d.annual_leave_entitlement
ORDER BY days_over_entitlement DESC, d.emp_id;
