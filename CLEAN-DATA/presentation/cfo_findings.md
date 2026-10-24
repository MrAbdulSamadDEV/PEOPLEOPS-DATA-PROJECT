# Indus Weave Textiles: top three findings for the CFO

Period: 1 April to 30 September 2026. All figures come from the warehouse and are reproduced by `python run_pipeline.py`. Evidence queries are in `analytics/`, results in `analytics/results/`.

## 1. Overtime cost is rising because of unsupported approvals in Stitching

**Number.** Paid overtime rose from 5,526 hours in April to 6,418 hours in September (+892 hours). Stitching alone rose by 1,017 hours (761.5 to 1,778.5), more than the whole increase. In Stitching, 644 approved overtime requests (1,947.5 hours, for 151 employees) fall on days when the employee did not work any overtime by punch. Estimated cost at Stitching's average overtime rate of 492.75 PKR/hour: about 960,000 PKR.

**Evidence.** Q5 (overtime three-way comparison) and Q6 (paid vs computed overtime by department). Stitching paid overtime is 56% above computed overtime; every other department is 7% to 16% below it. The 644 requests are all approved by one approver, E10382 (Kashif Hashmi, Assistant Manager, Stitching). Of the 622 cases where the employee was present, the shift ended on time or the overtime was not worked; 22 cases were absence days. Monthly unsupported hours grew from 49 (April) to 662 (September).

**Action.** Freeze payment of Stitching overtime approvals that have no punch-based overtime, pending review. Require a second approver for any overtime request above a set threshold, and do not let one person approve all of a department's overtime. Reconcile approved overtime against punches before each payroll run.

## 2. Six active employees are paid with zero attendance and no biometric enrolment

**Number.** Six employees (E10399, E11064, E10491, E11089, E10907, E10564) have no device mapping, so no punches at all in six months. They are recorded as Absent on 884 days in total (about 147 each) and received 2,877,075 PKR gross pay. None of them has an ABSENCE_DEDUCTION line, while 1,180 other employees do.

**Evidence.** Q7 (employees paid in a month with zero attendance) and the device mapping gap in `device_mapping.csv`. Six employees have no device row, and these six are exactly the employees with zero punches and no absence deduction.

**Action.** Verify each of the six employees (existence, identity, bank account, and manager sign-off) before the next payroll. Suspend payment until verified. Recover the amounts if they cannot be verified. Make biometric enrolment a condition of activation in the HCM system.

## 3. Five separated employees are still being paid

**Number.** Five employees were paid after their separation date: 21 payslips, 1,948,000 PKR gross, continuing through September 2026. The payments are still going out for the latest months.

**Evidence.** Q8 (employees still receiving pay after separation date). Cross-checked against the raw files, which give the same 21 payslips for the same 5 employees.

**Action.** Stop the payments now. Recover overpaid amounts. Add a payroll control that blocks any payslip for an employee whose separation date is before the payroll month.

## Other things the CFO should know

- Q10: 20 employees have already taken more Annual leave in six months than their full-year entitlement, mostly in Spinning and Finishing (up to 28 days against 14).
- Attendance data needed a correction: the SITE Plant biometric device ran one hour fast from 1 July 2026. Without the correction, SITE late arrivals would be inflated for the last three months.
- Punched overtime exceeded approved overtime by about 3.6% across the rest of the company. This is unpaid overtime worked, which is a labour-law risk to review.
