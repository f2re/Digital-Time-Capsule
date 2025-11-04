# migrations/versions/007_add_user_timezone.py
"""
Migration: Add timezone field to users table
Version: 007
Description: Adds user timezone support to properly handle local times
"""
from sqlalchemy import text, inspect


def upgrade(engine):
    """Add timezone column to users table"""
    with engine.connect() as conn:
        inspector = inspect(engine)

        # Check if column already exists
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'timezone' in columns:
            print("⚠ Column timezone already exists")
            return

        # Detect database type
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            # SQLite
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC' NOT NULL"
            ))
            conn.commit()
            print("✓ Added timezone column with default 'UTC' (SQLite)")

        elif 'postgresql' in db_url:
            # PostgreSQL - with IF NOT EXISTS for safety
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC' NOT NULL"
            ))
            conn.commit()
            print("✓ Added timezone column with default 'UTC' (PostgreSQL)")

        else:
            print("⚠ Unsupported database type")


def downgrade(engine):
    """Remove timezone column from users table"""
    with engine.connect() as conn:
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            print("⚠ SQLite doesn't support DROP COLUMN easily. Manual migration needed.")
            # SQLite requires recreating the entire table to drop a column
            # Not implemented for safety

        elif 'postgresql' in db_url:
            conn.execute(text(
                "ALTER TABLE users DROP COLUMN IF EXISTS timezone"
            ))
            conn.commit()
            print("✓ Removed timezone column (PostgreSQL)")