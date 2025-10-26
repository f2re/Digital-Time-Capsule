# src/migrations/migration_manager.py

import os
import importlib
from datetime import datetime
from typing import List, Dict, Tuple
from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, MetaData, text, inspect
from ..config import DATABASE_URL, logger
from ..database import engine, metadata

# Migration tracking table
migration_history = Table('migration_history', metadata,
    Column('id', Integer, primary_key=True),
    Column('version', String(50), unique=True, nullable=False),
    Column('name', String(255), nullable=False),
    Column('applied_at', DateTime, default=datetime.utcnow),
    Column('success', Boolean, default=True),
    Column('error_message', String(1000), nullable=True),
    extend_existing=True
)

def init_migration_table():
    """Create migration tracking table if it doesn't exist"""
    try:
        inspector = inspect(engine)
        if not inspector.has_table('migration_history'):
            migration_history.create(engine)
            logger.info("✅ Migration history table created")
        return True
    except Exception as e:
        logger.error(f"Error creating migration history table: {e}")
        return False

def get_applied_migrations() -> List[str]:
    """Get list of already applied migration versions"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT version FROM migration_history WHERE success = true ORDER BY version")
            )
            return [row[0] for row in result]
    except Exception as e:
        logger.warning(f"Could not fetch applied migrations: {e}")
        return []

def get_available_migrations() -> List[Tuple[str, str, object]]:
    """
    Scan migrations/versions directory and return available migrations
    Returns list of (version, name, module) tuples
    """
    migrations = []
    versions_dir = os.path.join(os.path.dirname(__file__), 'versions')

    if not os.path.exists(versions_dir):
        logger.warning(f"Migrations directory not found: {versions_dir}")
        return migrations

    for filename in sorted(os.listdir(versions_dir)):
        if filename.endswith('.py') and not filename.startswith('__'):
            # Extract version from filename (e.g., "001_add_capsule_balance.py")
            version = filename.split('_')[0]
            name = filename[:-3]  # Remove .py extension

            try:
                # Import the migration module
                module_path = f"src.migrations.versions.{name}"
                module = importlib.import_module(module_path)

                # Verify module has required functions
                if hasattr(module, 'upgrade') and hasattr(module, 'downgrade'):
                    migrations.append((version, name, module))
                else:
                    logger.warning(f"Migration {name} missing upgrade/downgrade functions")
            except Exception as e:
                logger.error(f"Error loading migration {name}: {e}")

    return migrations

def record_migration(version: str, name: str, success: bool = True, error: str = None):
    """Record migration application in history"""
    try:
        with engine.connect() as conn:
            conn.execute(
                migration_history.insert().values(
                    version=version,
                    name=name,
                    applied_at=datetime.utcnow(),
                    success=success,
                    error_message=error
                )
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error recording migration: {e}")

def apply_migration(version: str, name: str, module) -> bool:
    """Apply a single migration"""
    logger.info(f"📦 Applying migration {version}: {name}")

    try:
        # Check if migration was already applied
        applied = get_applied_migrations()
        if version in applied:
            logger.info(f"⏭️  Migration {version} already applied, skipping")
            return True

        # Execute upgrade function
        module.upgrade(engine)

        # Record successful migration
        record_migration(version, name, success=True)
        logger.info(f"✅ Migration {version} applied successfully")
        return True

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error applying migration {version}: {error_msg}")
        record_migration(version, name, success=False, error=error_msg)
        return False

def run_migrations() -> bool:
    """
    Main migration runner - automatically applies pending migrations
    Returns True if all migrations successful, False otherwise
    """
    logger.info("🔄 Starting database migration check...")

    try:
        # Initialize migration tracking table
        if not init_migration_table():
            logger.error("Failed to initialize migration table")
            return False

        # Get applied and available migrations
        applied = get_applied_migrations()
        available = get_available_migrations()

        if not available:
            logger.info("📋 No migration files found")
            return True

        # Find pending migrations
        pending = [m for m in available if m[0] not in applied]

        if not pending:
            logger.info(f"✅ All migrations up to date ({len(applied)} applied)")
            return True

        logger.info(f"📦 Found {len(pending)} pending migration(s)")

        # Apply each pending migration in order
        success_count = 0
        for version, name, module in pending:
            if apply_migration(version, name, module):
                success_count += 1
            else:
                logger.error(f"❌ Migration {version} failed, stopping migration process")
                return False

        logger.info(f"🎉 Successfully applied {success_count} migration(s)")
        return True

    except Exception as e:
        logger.error(f"❌ Critical error during migration: {e}")
        return False

def get_migration_status() -> Dict:
    """Get current migration status for debugging"""
    try:
        applied = get_applied_migrations()
        available = get_available_migrations()
        pending = [m for m in available if m[0] not in applied]

        return {
            'applied_count': len(applied),
            'available_count': len(available),
            'pending_count': len(pending),
            'applied_versions': applied,
            'pending_versions': [m[0] for m in pending]
        }
    except Exception as e:
        logger.error(f"Error getting migration status: {e}")
        return {'error': str(e)}

def rollback_migration(version: str) -> bool:
    """Rollback a specific migration (use with caution)"""
    logger.warning(f"⚠️  Rolling back migration {version}")

    try:
        available = get_available_migrations()
        migration = next((m for m in available if m[0] == version), None)

        if not migration:
            logger.error(f"Migration {version} not found")
            return False

        _, name, module = migration

        # Execute downgrade function
        module.downgrade(engine)

        # Remove from migration history
        with engine.connect() as conn:
            conn.execute(
                text(f"DELETE FROM migration_history WHERE version = :version"),
                {"version": version}
            )
            conn.commit()

        logger.info(f"✅ Migration {version} rolled back successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error rolling back migration {version}: {e}")
        return False
