# src/migrations/versions/002_add_transactions_table.py
"""
Migration: Create transactions table
Version: 002
Description: Adds transactions table for tracking capsule purchases
"""

from sqlalchemy import text, inspect

def upgrade(engine):
    """Create transactions table"""
    with engine.connect() as conn:
        inspector = inspect(engine)

        # Check if table already exists
        if inspector.has_table('transactions'):
            print("  ⏭  Table 'transactions' already exists")
            return

        db_url = str(engine.url)

        if 'sqlite' in db_url:
            conn.execute(text("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    transaction_type VARCHAR(50),
                    stars_paid INTEGER,
                    capsules_added INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    telegram_payment_charge_id VARCHAR(255) UNIQUE,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            conn.commit()
            print("  ✓ Created transactions table (SQLite)")

        elif 'postgresql' in db_url:
            conn.execute(text("""
                CREATE TABLE transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    transaction_type VARCHAR(50),
                    stars_paid INTEGER,
                    capsules_added INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    telegram_payment_charge_id VARCHAR(255) UNIQUE,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            conn.commit()
            print("  ✓ Created transactions table (PostgreSQL)")

        # Create index for faster queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_transactions_user_id
            ON transactions(user_id)
        """))
        conn.commit()
        print("  ✓ Created index on transactions.user_id")

def downgrade(engine):
    """Drop transactions table"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS transactions"))
        conn.commit()
        print("  ✓ Dropped transactions table")
