#!/usr/bin/env python3
"""
Migration script to add onboarding columns to users table
"""

from src.database import engine
from sqlalchemy import text

def migrate_onboarding():
    """Add onboarding columns to existing users table"""
    try:
        # For SQLite, check table info to see if columns exist
        with engine.connect() as conn:
            # Get table info
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns_info = result.fetchall()
            existing_columns = [col[1] for col in columns_info]  # col[1] is the column name
            
            # Check if onboarding_stage column exists
            if 'onboarding_stage' not in existing_columns:
                # Add onboarding_stage column
                conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_stage VARCHAR(50) DEFAULT 'not_started'"))
                print("✓ Added onboarding_stage column to users table")
            else:
                print("ℹ onboarding_stage column already exists")
            
            # Check if onboarding_variant column exists
            if 'onboarding_variant' not in existing_columns:
                # Add onboarding_variant column
                conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_variant VARCHAR(10) DEFAULT NULL"))
                print("✓ Added onboarding_variant column to users table")
            else:
                print("ℹ onboarding_variant column already exists")
                
            conn.commit()
            print("✓ Onboarding migration completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    migrate_onboarding()