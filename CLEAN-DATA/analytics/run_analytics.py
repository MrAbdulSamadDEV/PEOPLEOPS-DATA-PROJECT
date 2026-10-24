"""Stage 5 - Run analytics queries and export results."""
from pathlib import Path
import pandas as pd

from config import ANALYTICS_DIR
from db import get_engine


def run():
    """Stage 5: Run all 10 analytics queries."""
    print("Stage 5 - Analytics")
    
    results_dir = ANALYTICS_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    engine = get_engine()
    analytics_dir = ANALYTICS_DIR
    
    # Run queries 01-10
    for i in range(1, 11):
        query_file = analytics_dir / f"q{i:02d}_*.sql"
        
        # Find the actual file (with wildcards in name)
        matching_files = list(analytics_dir.glob(f"q{i:02d}_*.sql"))
        if not matching_files:
            print(f"  warning: q{i:02d} query file not found")
            continue
        
        query_file = matching_files[0]
        print(f"  running {query_file.name}")
        
        try:
            with open(query_file, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            df = pd.read_sql(sql, engine)
            
            # Save results
            output_file = results_dir / f"q{i:02d}_results.csv"
            df.to_csv(output_file, index=False)
            print(f"    saved {len(df)} rows to {output_file.name}")
        except Exception as e:
            print(f"    error: {e}")
    
    print("Stage 5 complete")
