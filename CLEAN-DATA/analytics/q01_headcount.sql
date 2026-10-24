-- Q1. Month-end headcount by plant and department, April to September 2026.
-- Rule 4: hired on or before month end and not separated on or before it.
-- Rule 3: department as of the last day of the month.
SELECT h.month_key        AS month,
       h.plant,
       dd.dept_id,
       dd.dept_name       AS department,
       h.headcount
FROM warehouse.v_headcount_month_end h
JOIN warehouse.dim_department dd ON dd.dept_id = h.dept_id
WHERE h.month_key BETWEEN '2026-04' AND '2026-09'
ORDER BY h.month_key, h.plant, dd.dept_name;
