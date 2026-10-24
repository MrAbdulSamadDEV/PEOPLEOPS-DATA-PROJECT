-- Q8. Employees still receiving pay after their separation date.
-- A payslip is after separation when its payroll month starts after the month
-- of the separation date (pay for the separation month itself is final pay).
SELECT de.emp_id,
       de.full_name,
       de.separation_date,
       p.payroll_month,
       dd.dept_name AS department,
       ROUND(SUM(CASE WHEN p.component_type = 'EARNING' THEN p.amount ELSE 0 END), 2) AS gross_earnings
FROM warehouse.fact_payroll_line p
JOIN warehouse.dim_employee de ON de.employee_sk = p.employee_sk
JOIN warehouse.dim_department dd ON dd.dept_id = p.dept_id
WHERE de.separation_date IS NOT NULL
  AND p.payroll_month > substr(de.separation_date, 1, 7)
GROUP BY de.emp_id, de.full_name, de.separation_date, p.payroll_month, dd.dept_name
ORDER BY p.payroll_month, de.emp_id;
