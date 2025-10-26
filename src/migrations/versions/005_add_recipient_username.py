# migrations/versions/005_add_recipient_username.py
"""
Migration: Add recipient_username field to capsules table
Version: 005
Description: Enables username-based capsule delivery (@username support)
"""
from sqlalchemy import text, inspect


def upgrade(engine):
    """Add recipient_username column to capsules table"""
    with engine.connect() as conn:
        inspector = inspect(engine)

        # Check if column already exists
        columns = [col['name'] for col in inspector.get_columns('capsules')]
        if 'recipient_username' in columns:
            print("⚠ Column recipient_username already exists")
            return

        # Detect database type
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            # SQLite
            conn.execute(text(
                "ALTER TABLE capsules ADD COLUMN recipient_username VARCHAR(255)"
            ))
            conn.commit()
            print("✓ Added recipient_username column (SQLite)")

        elif 'postgresql' in db_url:
            # PostgreSQL - with IF NOT EXISTS for safety
            conn.execute(text(
                "ALTER TABLE capsules ADD COLUMN IF NOT EXISTS recipient_username VARCHAR(255)"
            ))
            conn.commit()
            print("✓ Added recipient_username column (PostgreSQL)")

        else:
            print("⚠ Unsupported database type")


def downgrade(engine):
    """Remove recipient_username column from capsules table"""
    with engine.connect() as conn:
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            print("⚠ SQLite doesn't support DROP COLUMN easily. Manual migration needed.")
            # SQLite requires recreating the entire table to drop a column
            # Not implemented for safety

        elif 'postgresql' in db_url:
            conn.execute(text(
                "ALTER TABLE capsules DROP COLUMN IF EXISTS recipient_username"
            ))
            conn.commit()
            print("✓ Removed recipient_username column (PostgreSQL)")
