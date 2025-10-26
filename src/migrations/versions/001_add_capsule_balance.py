# src/migrations/versions/001_add_capsule_balance.py
"""
Migration: Add capsule_balance field to users table
Version: 001
Description: Adds capsule balance tracking for the new payment system
"""

from sqlalchemy import text
from datetime import datetime

def upgrade(engine):
    """Add capsule_balance column to users table"""
    with engine.connect() as conn:
        # Detect database type
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            # SQLite: Check if column exists before adding
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM pragma_table_info('users')
                WHERE name='capsule_balance'
            """))

            if result.scalar() == 0:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN capsule_balance INTEGER DEFAULT 0
                """))
                conn.commit()
                print("  ✓ Added capsule_balance column (SQLite)")
            else:
                print("  ⏭  Column capsule_balance already exists (SQLite)")

        elif 'postgresql' in db_url:
            # PostgreSQL: Use IF NOT EXISTS
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS capsule_balance INTEGER DEFAULT 0
            """))
            conn.commit()
            print("  ✓ Added capsule_balance column (PostgreSQL)")

        # Give existing free users 3 starter capsules
        conn.execute(text("""
            UPDATE users
            SET capsule_balance = 3
            WHERE subscription_status = 'free'
            AND (capsule_balance = 0 OR capsule_balance IS NULL)
        """))
        conn.commit()
        print("  ✓ Granted 3 starter capsules to existing free users")

def downgrade(engine):
    """Remove capsule_balance column from users table"""
    with engine.connect() as conn:
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            print("  ⚠️  SQLite doesn't support DROP COLUMN, manual migration required")
            # SQLite requires table recreation for column removal
            # This is intentionally not implemented for safety

        elif 'postgresql' in db_url:
            conn.execute(text("""
                ALTER TABLE users
                DROP COLUMN IF EXISTS capsule_balance
            """))
            conn.commit()
            print("  ✓ Removed capsule_balance column (PostgreSQL)")
