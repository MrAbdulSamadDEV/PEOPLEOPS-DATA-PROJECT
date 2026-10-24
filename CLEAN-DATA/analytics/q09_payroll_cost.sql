-- Q9. Payroll cost per employee by department, with month-over-month change.
-- Payroll cost = sum of EARNING lines (rule 21). Employees = distinct employees
-- paid that month. Department as of the reference date (rule 3).
WITH monthly AS (
    SELECT p.payroll_month AS month_key,
           p.dept_id,
           SUM(CASE WHEN p.component_type = 'EARNING' THEN p.amount ELSE 0 END) AS payroll_cost,
           COUNT(DISTINCT de.emp_id) AS paid_employees
    FROM warehouse.fact_payroll_line p
    JOIN warehouse.dim_employee de ON de.employee_sk = p.employee_sk
    GROUP BY p.payroll_month, p.dept_id
),
per_employee AS (
    SELECT month_key, dept_id, payroll_cost, paid_employees,
           payroll_cost * 1.0 / paid_employees AS cost_per_employee
    FROM monthly
)
SELECT pe.month_key AS month,
       dd.plant,
       dd.dept_name AS department,
       ROUND(pe.payroll_cost, 2)        AS payroll_cost,
       pe.paid_employees,
       ROUND(pe.cost_per_employee, 2)   AS cost_per_employee,
       ROUND(pe.cost_per_employee - LAG(pe.cost_per_employee) OVER w, 2) AS mom_change_amount,
       ROUND(100.0 * (pe.cost_per_employee / LAG(pe.cost_per_employee) OVER w - 1), 2) AS mom_change_pct
FROM per_employee pe
JOIN warehouse.dim_department dd ON dd.dept_id = pe.dept_id
WINDOW w AS (PARTITION BY pe.dept_id ORDER BY pe.month_key)
ORDER BY pe.month_key, dd.plant, dd.dept_name;
