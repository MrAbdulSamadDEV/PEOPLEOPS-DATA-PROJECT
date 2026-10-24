# PeopleOps Data Project

A Python and SQL-based HR analytics pipeline for transforming raw Human Resources data into clean, analysis-ready datasets and a SQLite data warehouse.

**Repository:** [MrAbdulSamadDEV/PEOPLEOPS-DATA-PROJECT](https://github.com/MrAbdulSamadDEV/PEOPLEOPS-DATA-PROJECT)

## Project Overview

HR data often lives across separate employee, attendance, leave, overtime, payroll, and recruitment files. This project brings those sources into a repeatable pipeline so HR and business teams can investigate workforce trends, attendance exceptions, payroll discrepancies, and recruitment performance.

The project is designed around a layered workflow:

1. **Raw ingestion** — load source CSV/JSON files while preserving source data and adding ingestion metadata.
2. **Staging and cleaning** — standardize records, handle duplicate employee records, map biometric devices, identify duplicate punches, and flatten leave approvals.
3. **Attendance processing** — derive daily attendance measures and flag cases that need review.
4. **Data warehouse** — organize cleaned HR data into dimensions and facts for reporting.
5. **Analytics** — run SQL queries that produce business-focused CSV outputs.
6. **Data quality** — run validation checks and report potential issues.

## Data Sources

The pipeline is designed to work with the hackathon's synthetic HR dataset, including:

- Employees and departments
- Employment history
- Biometric punches and device mappings
- Shift rosters and shift definitions
- Holidays
- Leave requests and approvals
- Overtime requests
- Payroll lines
- Recruitment applications

Place the provided source files in the `data/` directory. Do not rename files unless the pipeline's input paths are updated accordingly.

## Technology Stack

- **Python** for orchestration and transformations
- **pandas** for tabular data processing
- **SQLite** for a portable local warehouse
- **SQL** for analytics and reporting
- **CSV/JSON** as source formats and report outputs

## Project Structure

```text
PEOPLEOPS-DATA-PROJECT/
├── data/                       # Source HR CSV and JSON files
├── analytics/
│   ├── q01_headcount.sql
│   ├── q02_attrition.sql
│   ├── q03_absenteeism.sql
│   ├── q04_late_arrivals.sql
│   ├── q05_overtime_reconciliation.sql
│   ├── q06_paid_exceeds_computed.sql
│   ├── q07_paid_zero_attendance.sql
│   ├── q08_pay_after_separation.sql
│   ├── q09_payroll_cost.sql
│   ├── q10_annual_leave_overuse.sql
│   └── results/                # Query result CSVs (if generated)
├── quality/
│   └── checks.py               # Data-quality validations
├── warehouse/
│   └── ddl/
│       └── schema.sql          # Warehouse schema definition
├── presentation/               # Findings and presentation material
├── output/                     # Local database and generated diagnostics
├── requirements.txt
├── README.md
└── run_pipeline.py              # Pipeline entry point
```

## Getting Started

### 1. Requirements

- Python 3.10 or newer
- pip

### 2. Install dependencies

From the project root, run:

```bash
python -m pip install -r requirements.txt
```

### 3. Add the source data

Put the provided CSV and JSON files in `data/`.

### 4. Run the pipeline

```bash
python run_pipeline.py
```

If the project includes a separate quality-check script, run it after the pipeline:

```bash
python quality/checks.py
```

## SQL Analytics

The analytics folder contains queries intended to investigate:

| Query | Business question |
|---|---|
| `q01_headcount.sql` | What is the employee headcount? |
| `q02_attrition.sql` | What patterns appear in employee attrition? |
| `q03_absenteeism.sql` | Where are absenteeism patterns emerging? |
| `q04_late_arrivals.sql` | Which late-arrival patterns need attention? |
| `q05_overtime_reconciliation.sql` | Do overtime requests reconcile with calculated hours? |
| `q06_paid_exceeds_computed.sql` | Where do paid overtime hours exceed computed hours? |
| `q07_paid_zero_attendance.sql` | Are overtime payments present without matching attendance? |
| `q08_pay_after_separation.sql` | Are payroll lines dated after an employee's separation? |
| `q09_payroll_cost.sql` | How does payroll cost vary across reporting groups? |
| `q10_annual_leave_overuse.sql` | Which employees may exceed annual leave allowances? |

The queries should be run against the warehouse tables created by the pipeline. Exact outputs depend on the supplied dataset.

## Data Quality and Interpretation

The pipeline is intended to help surface issues such as missing identifiers, duplicate records, duplicate biometric punches, unusual attendance values, device clock drift, overtime mismatches, and payroll entries after separation.

Important considerations:

- A detected anomaly is a **review flag**, not proof of fraud or misconduct.
- Device clock drift should be validated before timestamps are corrected.
- First/last-punch attendance logic may need special handling for overnight shifts.
- Payroll, overtime, leave, and attrition metrics should be checked against business definitions before being used for decisions.
- The included dataset is synthetic and should not be treated as real employee data.

## Outputs

Depending on which pipeline steps have been run, generated artifacts may include:

- A SQLite warehouse database under `output/`
- Data-quality results
- Device clock diagnostic reports
- SQL query result CSV files under `analytics/results/`
- Findings or presentation notes under `presentation/`

Generated output files may not exist until the pipeline has been executed locally.

## Reproducibility

To reproduce the analysis, use the same source dataset, Python dependencies, and pipeline version. Keep source files unchanged and regenerate outputs by rerunning the pipeline.

## Author

**Abdul Samad**  
GitHub: [@MrAbdulSamadDEV](https://github.com/MrAbdulSamadDEV)

---

*Built as an HR data engineering and analytics project focused on reliable ingestion, data quality, warehouse modeling, and practical workforce insights.*
