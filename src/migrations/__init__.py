# src/migrations/__init__.py
"""
Database Migration System for Digital Time Capsule
Automatically applies schema changes on bot startup
"""

from .migration_manager import run_migrations, get_migration_status

__all__ = ['run_migrations', 'get_migration_status']
