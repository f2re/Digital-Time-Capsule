#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration CLI Tool
Manage database migrations manually
"""

import sys
import argparse
from src.migrations.migration_manager import (
    run_migrations, get_migration_status, rollback_migration
)
from src.config import logger

def main():
    parser = argparse.ArgumentParser(description='Database Migration Tool')
    parser.add_argument('command', choices=['migrate', 'status', 'rollback'],
                      help='Migration command to execute')
    parser.add_argument('--version', help='Version to rollback (for rollback command)')

    args = parser.parse_args()

    if args.command == 'migrate':
        print("🔄 Running database migrations...")
        success = run_migrations()
        sys.exit(0 if success else 1)

    elif args.command == 'status':
        print("📊 Migration Status:")
        status = get_migration_status()
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
            sys.exit(1)

        print(f"  Applied: {status['applied_count']}")
        print(f"  Available: {status['available_count']}")
        print(f"  Pending: {status['pending_count']}")

        if status['applied_versions']:
            print("\n  Applied versions:")
            for v in status['applied_versions']:
                print(f"    ✓ {v}")

        if status['pending_versions']:
            print("\n  Pending versions:")
            for v in status['pending_versions']:
                print(f"    • {v}")

    elif args.command == 'rollback':
        if not args.version:
            print("❌ Error: --version required for rollback")
            sys.exit(1)

        print(f"⚠️  Rolling back migration {args.version}...")
        success = rollback_migration(args.version)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
