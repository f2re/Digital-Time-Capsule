# src/migrations/versions/003_fix_recipient_id_type.py
"""
Migration: Fix recipient_id field type
Version: 003
Description: Change recipient_id from BigInteger to String to support usernames
"""

from sqlalchemy import text

def upgrade(engine):
    """Change recipient_id type to support both IDs and usernames"""
    with engine.connect() as conn:
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            # SQLite: Complex migration - need to recreate table
            # First, check if the column is already TEXT
            result = conn.execute(text("""
                SELECT type
                FROM pragma_table_info('capsules')
                WHERE name='recipient_id'
            """))

            col_type = result.scalar()

            if col_type and 'TEXT' not in col_type.upper() and 'VARCHAR' not in col_type.upper():
                # Need to migrate
                print("  ⚠️  SQLite detected - Manual intervention may be required")
                print("  ⚠️  recipient_id is currently INTEGER, needs to be TEXT")
                print("  ⚠️  Please backup your database and run manual migration if needed")
            else:
                print("  ✓ recipient_id column type is already compatible (SQLite)")

        elif 'postgresql' in db_url:
            # PostgreSQL: Alter column type
            try:
                conn.execute(text("""
                    ALTER TABLE capsules
                    ALTER COLUMN recipient_id TYPE VARCHAR(255)
                    USING recipient_id::VARCHAR
                """))
                conn.commit()
                print("  ✓ Changed recipient_id to VARCHAR(255) (PostgreSQL)")
            except Exception as e:
                if 'does not exist' in str(e):
                    print("  ⏭  Column recipient_id already migrated or doesn't exist")
                else:
                    raise

def downgrade(engine):
    """Revert recipient_id type change"""
    with engine.connect() as conn:
        db_url = str(engine.url)

        if 'postgresql' in db_url:
            print("  ⚠️  Warning: Downgrade may fail if non-numeric data exists")
            try:
                conn.execute(text("""
                    ALTER TABLE capsules
                    ALTER COLUMN recipient_id TYPE BIGINT
                    USING recipient_id::BIGINT
                """))
                conn.commit()
                print("  ✓ Reverted recipient_id to BIGINT (PostgreSQL)")
            except Exception as e:
                print(f"  ❌ Downgrade failed: {e}")
