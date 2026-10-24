"""Database connection and utilities. SQLAlchemy engine with attached schemas."""
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool

from config import RAW_DB, STAGING_DB, WAREHOUSE_DB


_engine = None


def get_engine():
    """Get or create the database engine with all three schemas attached."""
    global _engine
    if _engine is not None:
        return _engine
    
    # Use warehouse.sqlite as the main database, attach raw and staging
    url = f"sqlite:///{WAREHOUSE_DB}"
    _engine = create_engine(
        url,
        connect_args={"timeout": 30},
        poolclass=StaticPool,
        echo=False
    )
    
    # Attach other databases on every connection
    @event.listens_for(_engine, "connect")
    def attach_databases(dbapi_conn, connection_record):
        dbapi_conn.execute(f"PRAGMA foreign_keys = ON")
        dbapi_conn.execute(f"ATTACH DATABASE '{RAW_DB}' AS raw")
        dbapi_conn.execute(f"ATTACH DATABASE '{STAGING_DB}' AS staging")
    
    return _engine


def run_sql_script(sql):
    """Execute a SQL script with one or more statements."""
    engine = get_engine()
    with engine.begin() as conn:
        # Split by semicolon and execute each statement
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))


def run_sql_file(filepath):
    """Execute a SQL file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    run_sql_script(sql)


def query_one(sql):
    """Execute a query and return a single scalar value."""
    with get_engine().connect() as conn:
        result = conn.exec_driver_sql(sql)
        return result.scalar()


def query_all(sql):
    """Execute a query and return all rows."""
    with get_engine().connect() as conn:
        result = conn.exec_driver_sql(sql)
        return result.fetchall()


def reset_databases():
    """Delete all database files to start fresh."""
    for db_file in [RAW_DB, STAGING_DB, WAREHOUSE_DB]:
        if db_file.exists():
            db_file.unlink()
    
    # Reset the engine
    global _engine
    _engine = None
