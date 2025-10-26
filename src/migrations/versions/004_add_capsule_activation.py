"""
Migration: Add capsule activation tracking
Version: 004
Description: Add fields to track capsule activation status and pending invitations
"""

from sqlalchemy import text

def upgrade(engine):
    """Add activation fields to capsules table"""
    with engine.connect() as conn:
        db_url = str(engine.url)

        if 'sqlite' in db_url:
            # SQLite
            try:
                conn.execute(text("""
                    ALTER TABLE capsules ADD COLUMN is_activated BOOLEAN DEFAULT 0
                """))
                conn.execute(text("""
                    ALTER TABLE capsules ADD COLUMN activation_link TEXT
                """))
                conn.execute(text("""
                    ALTER TABLE capsules ADD COLUMN activated_at DATETIME
                """))
                conn.commit()
                print("  ✓ Added capsule activation fields (SQLite)")
            except Exception as e:
                if 'duplicate column' in str(e).lower():
                    print("  ⏭  Activation fields already exist (SQLite)")
                else:
                    raise

        elif 'postgresql' in db_url:
            # PostgreSQL
            try:
                conn.execute(text("""
                    ALTER TABLE capsules
                    ADD COLUMN IF NOT EXISTS is_activated BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS activation_link VARCHAR(500),
                    ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP
                """))
                conn.commit()
                print("  ✓ Added capsule activation fields (PostgreSQL)")
            except Exception as e:
                print(f"  ⚠️  Migration warning: {e}")

def downgrade(engine):
    """Remove activation fields"""
    with engine.connect() as conn:
        db_url = str(engine.url)

        if 'postgresql' in db_url:
            try:
                conn.execute(text("""
                    ALTER TABLE capsules
                    DROP COLUMN IF EXISTS is_activated,
                    DROP COLUMN IF EXISTS activation_link,
                    DROP COLUMN IF EXISTS activated_at
                """))
                conn.commit()
                print("  ✓ Removed capsule activation fields (PostgreSQL)")
            except Exception as e:
                print(f"  ❌ Downgrade failed: {e}")
        else:
            print("  ⚠️  SQLite doesn't support DROP COLUMN easily")
