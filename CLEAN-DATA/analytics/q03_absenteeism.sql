-- Q3. Absenteeism rate by plant and month, excluding approved leave.
-- Absent days / scheduled days. Scheduled days = Present + Absent + Missing Punch.
-- Weekly Off, Holiday and On Leave are not scheduled working days.
-- Plant as of the month end (rule 3).
WITH att AS (
    SELECT vem.plant,
           substr(dt.full_date, 1, 7) AS month_key,
           f.status
    FROM warehouse.fact_attendance_daily f
    JOIN warehouse.dim_employee de ON de.employee_sk = f.employee_sk
    JOIN warehouse.dim_date dt     ON dt.date_key = f.date_key
    JOIN warehouse.v_employee_month vem
      ON vem.emp_id = de.emp_id AND vem.month_key = substr(dt.full_date, 1, 7)
    WHERE dt.full_date BETWEEN '2026-04-01' AND '2026-09-30'
)
SELECT month_key AS month,
       plant,
       SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_days,
       SUM(CASE WHEN status IN ('Present', 'Absent', 'Missing Punch') THEN 1 ELSE 0 END) AS scheduled_days,
       ROUND(100.0 * SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN status IN ('Present', 'Absent', 'Missing Punch') THEN 1 ELSE 0 END), 0), 2)
             AS absenteeism_pct
FROM att
GROUP BY month_key, plant
ORDER BY month_key, plant;
