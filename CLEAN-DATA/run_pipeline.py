"""One-command rebuild of the whole pipeline from the raw files.

    python run_pipeline.py            # full rebuild (raw files are reloaded only if changed)
    python run_pipeline.py --clean    # delete db/ first and rebuild everything from scratch

Exit code 0 means every stage ran and no data quality check failed.
"""
import shutil
import sys
import time

from config import DB_DIR


def main(argv):
    if "--clean" in argv:
        shutil.rmtree(DB_DIR, ignore_errors=True)
        print("db/ removed; rebuilding from raw files")

    from ingestion import load_raw
    from transform import clean_staging, run_stage3
    from warehouse import build_warehouse
    from analytics import run_analytics
    from quality import run_checks, independent_recount

    started = time.time()
    load_raw.run(force="--clean" in argv)
    clean_staging.run()
    run_stage3.run()
    build_warehouse.run()
    run_analytics.run()
    passed = run_checks.run()
    print("Cross-check against an independent pandas recount")
    recount_ok = independent_recount.run()
    print(f"\nFinished in {time.time() - started:.1f}s. "
          f"Data quality: {'PASS' if passed else 'FAILED'}. "
          f"Independent recount: {'MATCH' if recount_ok else 'DIFFERENCES FOUND'}.")
    return 0 if (passed and recount_ok) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
