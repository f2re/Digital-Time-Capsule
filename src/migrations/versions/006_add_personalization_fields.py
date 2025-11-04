"""Add personalization fields

Migration ID: 003
Description: Add fields for user personalization beyond basic onboarding
"""

from sqlalchemy import text


def upgrade(connection, database_type='sqlite'):
    """Add personalization fields to users table (skip if exist)"""
    
    # For SQLite, we need to check each column individually since it doesn't support IF NOT EXISTS
    if database_type == 'sqlite':
        # Check and add each column individually
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN onboarding_started_at TIMESTAMP DEFAULT NULL"))
        except:
            print("Column onboarding_started_at already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN onboarding_completed_at TIMESTAMP DEFAULT NULL"))
        except:
            print("Column onboarding_completed_at already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN last_activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        except:
            print("Column last_activity_time already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN preferred_capsule_types TEXT DEFAULT '{}'"))
        except:
            print("Column preferred_capsule_types already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN emotional_profile VARCHAR(50) DEFAULT 'unknown'"))
        except:
            print("Column emotional_profile already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN streak_count INTEGER DEFAULT 0"))
        except:
            print("Column streak_count already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN best_streak INTEGER DEFAULT 0"))
        except:
            print("Column best_streak already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN total_capsules_created INTEGER DEFAULT 0"))
        except:
            print("Column total_capsules_created already exists, skipping")
        
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN engagement_score REAL DEFAULT 0.0"))
        except:
            print("Column engagement_score already exists, skipping")
    
    # For PostgreSQL, use the IF NOT EXISTS syntax (if supported) or use a try-except approach
    else:  # PostgreSQL and other DBs
        additional_fields = [
            "ALTER TABLE users ADD COLUMN onboarding_started_at TIMESTAMP DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN onboarding_completed_at TIMESTAMP DEFAULT NULL", 
            "ALTER TABLE users ADD COLUMN last_activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE users ADD COLUMN preferred_capsule_types JSON DEFAULT '{}'",
            "ALTER TABLE users ADD COLUMN emotional_profile VARCHAR(50) DEFAULT 'unknown'",
            "ALTER TABLE users ADD COLUMN streak_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN best_streak INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN total_capsules_created INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN engagement_score REAL DEFAULT 0.0"
        ]
        
        for field_sql in additional_fields:
            try:
                connection.execute(text(field_sql))
            except Exception as e:
                print(f"Field might already exist: {e}")


def downgrade(connection, database_type='sqlite'):
    """Remove personalization fields (SQLite doesn't support DROP COLUMN easily)"""
    if database_type == 'postgresql':
        fields_to_drop = [
            'onboarding_started_at', 'onboarding_completed_at', 'last_activity_time', 
            'preferred_capsule_types', 'emotional_profile', 'streak_count', 
            'best_streak', 'total_capsules_created', 'engagement_score'
        ]
        for field in fields_to_drop:
            try:
                connection.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {field}"))
            except Exception:
                print(f"Field {field} might not exist or drop not supported")
    else:
        print("SQLite doesn't support DROP COLUMN - manual cleanup required")