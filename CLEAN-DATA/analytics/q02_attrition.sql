-- Q2. Monthly attrition rate by department: separations / average headcount.
-- Separations are attributed to the department on the last working day (rule 3).
-- Average headcount = (opening headcount at the previous month end + closing headcount) / 2.
WITH months AS (
    SELECT month_key,
           LAG(month_key) OVER (ORDER BY month_key) AS prev_key
    FROM warehouse.v_month
),
headcount AS (
    SELECT month_key, dept_id, headcount FROM warehouse.v_headcount_month_end
),
separations AS (
    SELECT vem.month_key, vem.dept_id, COUNT(*) AS separations
    FROM warehouse.v_employee_month vem
    JOIN warehouse.dim_employee d ON d.employee_sk = vem.employee_sk
    WHERE d.separation_date IS NOT NULL
      AND substr(d.separation_date, 1, 7) = vem.month_key
      AND vem.reference_date = d.separation_date
    GROUP BY vem.month_key, vem.dept_id
),
base AS (
    SELECT m.month_key,
           dd.plant,
           dd.dept_id,
           dd.dept_name,
           COALESCE(op.headcount, 0)    AS opening_headcount,
           COALESCE(cl.headcount, 0)    AS closing_headcount,
           COALESCE(s.separations, 0)   AS separations
    FROM months m
    CROSS JOIN warehouse.dim_department dd
    LEFT JOIN headcount op ON op.month_key = m.prev_key AND op.dept_id = dd.dept_id
    LEFT JOIN headcount cl ON cl.month_key = m.month_key AND cl.dept_id = dd.dept_id
    LEFT JOIN separations s ON s.month_key = m.month_key AND s.dept_id = dd.dept_id
    WHERE m.month_key BETWEEN '2026-04' AND '2026-09'
)
SELECT month_key AS month,
       plant,
       dept_id,
       dept_name AS department,
       opening_headcount,
       closing_headcount,
       separations,
       ROUND((opening_headcount + closing_headcount) / 2.0, 2) AS average_headcount,
       ROUND(separations * 1.0 / NULLIF((opening_headcount + closing_headcount) / 2.0, 0), 4) AS attrition_rate
FROM base
WHERE opening_headcount + closing_headcount + separations > 0
ORDER BY month, plant, department;
