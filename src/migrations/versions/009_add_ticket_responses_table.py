"""
Add ticket responses table

Revision ID: 009
Revises: 008
Create Date: 2024-11-06 12:00:00.000000

"""
from sqlalchemy import text
from datetime import datetime

# revision identifiers
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade(engine):
    """Create ticket_responses table"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ticket_responses (
                id INTEGER NOT NULL,
                ticket_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME,
                is_admin_response BOOLEAN NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(ticket_id) REFERENCES support_tickets (id),
                FOREIGN KEY(user_id) REFERENCES users (id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ticket_responses_ticket_id ON ticket_responses (ticket_id)"))
        conn.commit()
    print("✅ ticket_responses table created")


def downgrade(engine):
    """Drop ticket_responses table"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE ticket_responses"))
        conn.commit()
    print("✅ ticket_responses table dropped")