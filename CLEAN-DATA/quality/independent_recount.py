"""Independent verification of key metrics using pandas."""
import pandas as pd
from db import get_engine


def run():
    """Recount key metrics independently and verify they match SQL results."""
    print("Independent recount (pandas verification)")
    
    engine = get_engine()
    all_match = True
    
    try:
        # Load data directly
        employees = pd.read_sql("SELECT * FROM staging.employees", engine)
        payroll = pd.read_sql("SELECT * FROM raw.payroll_lines", engine)
        
        # Count distinct employees
        pandas_emp_count = employees['emp_id'].nunique()
        sql_emp_count = pd.read_sql(
            "SELECT COUNT(DISTINCT emp_id) AS count FROM staging.employees",
            engine
        )['count'][0]
        
        if pandas_emp_count == sql_emp_count:
            print(f"    [ok  ] employee count: {pandas_emp_count}")
        else:
            print(f"    [FAIL] employee count: pandas={pandas_emp_count}, sql={sql_emp_count}")
            all_match = False
        
        # Count payroll lines
        pandas_pay_count = len(payroll)
        sql_pay_count = pd.read_sql(
            "SELECT COUNT(*) AS count FROM raw.payroll_lines",
            engine
        )['count'][0]
        
        if pandas_pay_count == sql_pay_count:
            print(f"    [ok  ] payroll line count: {pandas_pay_count}")
        else:
            print(f"    [FAIL] payroll line count: pandas={pandas_pay_count}, sql={sql_pay_count}")
            all_match = False
        
        print("Independent recount complete")
        return all_match
    except Exception as e:
        print(f"    [FAIL] {e}")
        return False
