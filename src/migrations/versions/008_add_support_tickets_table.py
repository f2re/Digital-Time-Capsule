"""
Add support tickets table

Revision ID: 008
Revises: 007_add_user_timezone
Create Date: 2024-11-05 10:00:00.000000

"""
from sqlalchemy import text
from datetime import datetime

# revision identifiers
revision = '008'
down_revision = '007_add_user_timezone'
branch_labels = None
depends_on = None


def upgrade(engine):
    """Create support_tickets table"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                subject VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at DATETIME,
                updated_at DATETIME,
                PRIMARY KEY (id),
                FOREIGN KEY(user_id) REFERENCES users (id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_support_tickets_user_id ON support_tickets (user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_support_tickets_status ON support_tickets (status)"))
        conn.commit()
    print("✅ Support tickets table created")


def downgrade(engine):
    """Drop support_tickets table"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE support_tickets"))
        conn.commit()
    print("✅ Support tickets table dropped")
