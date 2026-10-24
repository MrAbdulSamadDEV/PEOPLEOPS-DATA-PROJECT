# Indus Weave Textiles: HR data pipeline (PeopleOps Data Hackathon)

A Python and SQL pipeline that turns six months of HCM exports into a trusted warehouse, answers the ten business questions, proves the numbers with data quality checks, and gives the CFO three findings.

Team members: _(fill in)_

## Quick start

Requirements: Python 3.10 or later. No database server is needed.

```bash
pip install -r requirements.txt
python run_pipeline.py --clean
```

A clean rebuild takes about 40 seconds. The pipeline ends with `Data quality: PASS` and `Independent recount: MATCH`. Output files are written to `db/` (three SQLite files: `raw.sqlite`, `staging.sqlite`, `warehouse.sqlite`) and to `analytics/results/`.

Running `python run_pipeline.py` without `--clean` is idempotent: unchanged raw files are skipped, and the warehouse is rebuilt from the same inputs, giving the same numbers.

## Layout

```
run_pipeline.py          one-command rebuild (all stages, checks, cross-check)
config.py                paths, analysis period, business constants
db.py                    connection; raw, staging and warehouse attached as schemas
data/raw/                the 12 HCM exports and data_dictionary.md (never edited by hand)
ingestion/load_raw.py    Stage 1: raw schema, all TEXT, load metadata, idempotent
transform/clean_staging.py  Stage 2: cleaning and standardization (Python)
transform/sql/stage3_attendance_daily.sql  Stage 3: business logic (SQL)
warehouse/ddl/           Stage 4: star schema DDL, reporting views
warehouse/load/          Stage 4: dimension and fact loads (SQL)
warehouse/erd.png        entity-relationship diagram (source: erd.dot)
analytics/q01..q10_*.sql one SQL file per business question
analytics/results/       one CSV per question
quality/run_checks.py    Stage 6: 78 checks, written to warehouse.dq_results
quality/independent_recount.py  headline answers recomputed in pandas from raw files
presentation/            cfo_findings.md, slides.pdf
```

## Design decisions

- **Database: SQLite.** PostgreSQL is not available in the build environment, and the brief allows SQLite. Three files correspond to the raw, staging and warehouse schemas; each is attached under its schema name, so SQL reads `raw.employees`, `staging.punches_clean` and `warehouse.dim_employee`. The SQL uses only standard constructs (CTEs, window functions, recursive CTEs), so porting to PostgreSQL is mechanical.
- **Raw layer is untouched.** Every value is stored as text. JSON files are kept as one payload per record (nothing flattened). A file is reloaded only if its SHA-256 changes, and every load checks rows-in-file against rows-loaded.
- **Reconciliation everywhere.** Every rejected row goes to a `rejected_*` table with a reason, so raw = staging + rejected holds for each table. Duplicates, unmapped punches and superseded history rows are all accounted for.
- **SCD Type 2 employees.** `dim_employee` has one row per employment version from `employment_history` (rule 2). Facts resolve the employee with `work_date BETWEEN valid_from AND valid_to`.
- **Monthly department rule (rule 3).** Monthly figures use the department on the last day of the month, or on the last working day for leavers. This is implemented once, in the view `v_employee_month`, and every monthly answer uses it.
- **Reporting views.** `v_headcount_month_end` (rule 4) and `v_employee_month` are the only places these rules are written.

## How the planted issues were found and fixed

| Issue | How it was found | Fix |
|---|---|---|
| 50 duplicate employees | Duplicate `emp_id` in raw | Kept latest `updated_at`; 50 rows in `rejected_employees` |
| Three date formats | Pattern profiling per column | Explicit parsers per format; no `dayfirst` guessing |
| Department text messy; two renamed departments | Distinct value profiling | Normalized text, mapped by (plant, name) and by `previous_name` |
| `effective_to` unreliable (39 rows) | Compared with next record's `effective_from - 1` | Recomputed; source value kept for audit |
| Same-day hire and salary change (E11259) | Overlapping `effective_from` | Same-day change kept; superseded row rejected with reason |
| Missing roster weeks (2,424) | Grid of employee x week | Filled from previous week (rule 6) |
| 6,962 unmapped punches | Device user not in `device_mapping` | Rejected with reason `UNMAPPED_DEVICE_USER` |
| 16,175 duplicate punches | Gaps of seconds between punches | Rejected with reason `DUPLICATE_WITHIN_2_MIN` |
| `DEV-SITE-01` clock +60 min from 1 July 2026 | Median check-in offset by device and day, against roster shift start: -7 min before 1 July, +53 min after | Corrected by -60 min for punches from 1 July 00:00. After correction every device's median is -7 min. |
| Night shifts | Punch hour distribution by shift | Shift date assigned from the roster; a morning punch belongs to the previous NIGHT shift unless the employee is on DAY that day |
| Approvals with no overtime worked | Joined approvals to punch-based overtime | Reported as a finding (CFO finding 1), not removed from the data |
| Ghost employees, post-separation pay | Payroll vs device mapping and separation dates | Reported as findings 2 and 3 |

## Assumptions and limitations

- **Night-shift checkout on a DAY morning.** On a day when the employee is rostered on DAY, a morning punch is taken as the DAY check-in. Where a NIGHT checkout also falls on that morning, it is not recovered. This affects 20 punches after separation dates (the WARN check `punches outside employment dates`). They are excluded from attendance and are documented.
- **Attendance grain.** One row per employee per day of employment in April to September (rule 4). Holidays and Sundays with no punches get status Holiday or Weekly Off.
- **Late and early minutes.** Counted only on Present working days, and only when the gap is more than the 10-minute grace (rule 13). The value is the full gap in minutes.
- **Overtime rounding.** Whole half-hours, rounded down (rule 14). Work on Sundays and plant holidays is all overtime (rule 15). Computed on the Present status only, so a leave day with punches does not add overtime.
- **Absenteeism denominator.** Scheduled days = Present + Absent + Missing Punch. Weekly Off, Holiday and On Leave are excluded.
- **Q7 attendance.** Zero attendance = no Present and no Missing Punch day in the month.
- **Q8.** A payslip is "after separation" when its payroll month is later than the separation month. Pay for the separation month itself is treated as final pay.
- **Q4 department.** Department on the employee's last working day in the period.
- **Q6.** Measured over the six months per department.
- **Recruitment funnel (bonus).** Not included in this submission.
- **Incremental load (bonus).** Only partly covered: unchanged raw files are skipped by hash. Row-level incremental loading for a new month of punches is not implemented.

## Verification

- 78 data quality checks (uniqueness, not-null, referential integrity, reconciliation, accepted values, business sanity). 77 PASS, 1 WARN (documented above). Results are in `warehouse.dq_results`.
- `quality/independent_recount.py` recomputes headcount, approved overtime, Stitching unsupported overtime, post-separation pay and leave overuse directly from raw files in pandas. All match the SQL results.
- Clean rebuild and repeat run both pass with identical row counts.

## AI assistance

AI assistants were used during the build. Every rule, query and check was reviewed against `data_dictionary.md`, and the independent recount was written to test the SQL logic. Team members should be able to explain every line in Q&A.
