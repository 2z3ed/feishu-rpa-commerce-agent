#!/usr/bin/env python3
"""
Run database migrations
"""
import sqlite3
import os

# Database path
DB_PATH = 'feishu_rpa.db'

# Migration SQL
MIGRATION_SQL = """
ALTER TABLE task_records ADD COLUMN target_task_id VARCHAR(64);
CREATE INDEX idx_task_records_target_task_id ON task_records(target_task_id);
"""

def run_migrations():
    """Run database migrations"""
    print(f"Running migrations on database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"Database file {DB_PATH} does not exist. Skipping migrations.")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if target_task_id column already exists
        cursor.execute("PRAGMA table_info(task_records)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'target_task_id' not in columns:
            print("Adding target_task_id column...")
            cursor.executescript(MIGRATION_SQL)
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("target_task_id column already exists. Skipping migration.")
            
    except Exception as e:
        print(f"Error running migrations: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_migrations()
