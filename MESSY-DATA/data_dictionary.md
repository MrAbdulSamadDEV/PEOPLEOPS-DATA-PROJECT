# Indus Weave Textiles — HCM Export Data Dictionary

Six months of exports (1 April – 30 September 2026) from the company's HCM platform.
Indus Weave Textiles is fictional. Every person, ID and number in these files is synthetic.

Plants: **Head Office** (Karachi), **Korangi Plant**, **SITE Plant**, **Faisalabad Plant**.

---

## Business rules

These rules are the "law" for this hackathon. Where the data disagrees with a rule, the rule wins.

### Employees and history
1. `employees.csv` may contain the same `emp_id` more than once. Keep the row with the latest `updated_at`.
2. `employment_history.csv` is the source of truth for department, grade and salary over time.
   The `effective_to` column in the export is **unreliable**. A record is valid from its
   `effective_from` until the day before that employee's next record starts. The latest record has no end.
3. Monthly figures (headcount, overtime, payroll cost) belong to the department the employee was in
   on the **last day of the month**, or on their last working day if they left during that month.
4. An employee is in headcount at month end if `hire_date` ≤ month end and they have no
   `separation_date`, or `separation_date` is after month end. `separation_date` is the last day worked.

### Shifts and roster
5. Plant workers rotate weekly between DAY, EVE and NIGHT shifts. Head Office and managers work GEN.
6. A roster week runs Monday to Sunday (`week_start` is the Monday).
   If an employee's week is missing from `shift_roster.csv`, they worked the **same shift as the previous week**.
7. A night-shift punch belongs to the **date the shift started**, not the calendar date of the punch.

### Punches
8. Each device user is mapped to an employee in `device_mapping.csv` by **`device_id` + `device_user_id`**.
   Punches with no mapping are contractors or visitors: exclude them, but keep them in a rejected table.
9. Two punches by the same employee within **2 minutes** of each other count as one.
10. For each employee and shift date, check-in = first punch, check-out = last punch.
    One punch only = **Missing Punch**.
11. Device clocks can drift. If you find a device whose times are wrong, correct them and explain how you found it.

### Attendance status (one per employee per day of employment)
12. Priority order:
    - Sunday with no punches → `Weekly Off`
    - Holiday for the employee's plant with no punches → `Holiday`
    - Covered by an approved leave → `On Leave`
    - Two or more punches → `Present`
    - One punch → `Missing Punch`
    - No punches → `Absent`
13. Late arrival = check-in more than **10 minutes** after shift start. Early departure = check-out more than
    **10 minutes** before shift end. Count both only on `Present` working days (not on Sundays or holidays).
14. Overtime on a working day = minutes worked **after shift end**, rounded down to whole half-hours
    (29 min = 0 h, 45 min = 0.5 h, 75 min = 1.0 h).
15. Work on a Sunday or holiday is **all overtime**: (check-out − check-in), rounded down to whole half-hours.

### Leave
16. A leave request counts only if **both approval steps** (Manager, then HR) say `Approved`
    and `cancelled_at` is empty.
17. A leave day is any day in the request's `from`–`to` range. Sundays and plant holidays inside the range
    are not leave days (rule 12 already gives them their own status).
18. `annual_leave_entitlement` is the employee's full-year entitlement for Annual leave.

### Overtime and payroll
19. Only overtime requests with `status = Approved` count as approved overtime.
20. Payroll pays overtime from approved requests. In `payroll_lines.csv` the `OVERTIME` line's `units` = hours paid.
21. Payroll cost = sum of `EARNING` lines. Deductions are shown as positive amounts with `component_type = DEDUCTION`.

---

## Files

### `employees.csv` — Core HR: People
| Column | Type | Notes |
|---|---|---|
| emp_id | text | E10001… |
| full_name, gender, email, phone | text | Synthetic |
| date_of_birth, hire_date, separation_date | text | Mixed formats: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-Mon-YYYY` |
| plant, department | text | Department text is messy: casing, spaces, old names |
| designation, grade | text | Grade G1–G9 |
| employment_type | text | Permanent / Contract |
| status | text | Active / Separated |
| annual_leave_entitlement | int | Days per year |
| updated_at | timestamp | Use to pick the latest duplicate |

### `departments.csv` — Foundation: Organization
`dept_id, dept_name, plant, cost_center, previous_name, renamed_on`. Two departments were renamed; `previous_name` shows the old name.

### `employment_history.csv` — Core HR: Employment
`emp_id, effective_from, effective_to, dept_id, designation, grade, basic_salary, change_reason`
(Hire, Salary Revision, Promotion, Transfer). Basic salary is monthly, in PKR.

### `shifts.json` — Workforce: Shifts
Four shifts with `start_time`, `end_time`, `crosses_midnight`, `grace_minutes`.

### `shift_roster.csv` — Workforce: Rosters
`emp_id, week_start, shift_code`. Includes planned weeks into October.

### `device_mapping.csv` — Workforce: Biometric Gateway
`device_id, device_user_id, emp_id, enrolled_on`.

### `biometric_punches.csv` — Workforce: Biometric Gateway
`punch_id, device_id, device_user_id, punch_time`. Raw device events, no direction (in/out) flag.
Includes the early-morning 1 October check-outs of 30 September night shifts.

### `holidays.csv` — Workforce: Holidays
`holiday_date, holiday_name, scope`. Scope `ALL` applies to every plant; `HO`, `KOR`, `SITE`, `FSD` apply to one plant only.

### `leave_requests.json` — Workforce: Leave
Array of requests. Each has `request_id`, `employee {emp_id, plant}`, `leave {type, from, to, days_requested}`,
`submitted_at`, `approvals [ {step, approver_role, approver_id, action, acted_at} ]` and `cancelled_at`.
`days_requested` is calendar days as typed by the employee; don't trust it for counting.

### `overtime_requests.csv` — Workforce: Overtime
`request_id, emp_id, ot_date, requested_hours, approved_hours, status, approver_id, requested_at`.
`ot_date` is the shift date.

### `payroll_lines.csv` — Payroll: Payslips
`line_id, payroll_month (YYYY-MM), emp_id, component, component_type, units, amount`.
Components: BASIC, HOUSE_RENT, MEDICAL, CONVEYANCE, OVERTIME (units = hours), INCOME_TAX, EOBI,
ABSENCE_DEDUCTION (units = days), LOAN_INSTALLMENT.

### `applications.csv` — Talent Acquisition (bonus only)
`application_id, candidate_id, job_req_id, dept_id, stage, stage_date`. One row per stage change.
