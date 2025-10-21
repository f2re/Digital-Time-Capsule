#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Database Initialization Script
Creates tables for Digital Time Capsule bot
"""

import os
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, DateTime,
    ForeignKey, Boolean, BigInteger, Text, LargeBinary, Float
)
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found in environment variables.")
    print("   Please set DATABASE_URL in your .env file.")
    exit(1)

# Ensure PostgreSQL is being used
if not DATABASE_URL.startswith("postgresql"):
    print("❌ Error: This script is for PostgreSQL initialization only.")
    print("   Please check DATABASE_URL in your .env file.")
    print(f"   Current URL starts with: {DATABASE_URL.split(':')[0]}")
    exit(1)

print(f"📊 Initializing PostgreSQL database...")

try:
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()

    # Users table
    users = Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('telegram_id', BigInteger, unique=True, nullable=False, index=True),
        Column('username', String(255)),
        Column('first_name', String(255)),
        Column('language_code', String(10), default='ru'),
        Column('subscription_status', String(50), default='free'),
        Column('subscription_expires', DateTime, nullable=True),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('total_storage_used', BigInteger, default=0),
        Column('capsule_count', Integer, default=0)
    )

    # Capsules table
    capsules = Table('capsules', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('capsule_uuid', String(36), unique=True, nullable=False, index=True),
        Column('content_type', String(50), nullable=False),
        Column('content_text', Text, nullable=True),
        Column('file_key', LargeBinary, nullable=True),
        Column('s3_key', String(500), nullable=True),
        Column('file_size', BigInteger, default=0),
        Column('recipient_type', String(50), nullable=False),
        Column('recipient_id', BigInteger, nullable=True),
        Column('delivery_time', DateTime, nullable=False),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('delivered', Boolean, default=False),
        Column('delivered_at', DateTime, nullable=True),
        Column('message', Text, nullable=True)
    )

    # Payments table
    payments = Table('payments', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('payment_type', String(50), nullable=False),
        Column('amount', Float, nullable=False),
        Column('currency', String(10), nullable=False),
        Column('subscription_type', String(50), nullable=False),
        Column('payment_id', String(255), unique=True, nullable=False),
        Column('successful', Boolean, default=False),
        Column('created_at', DateTime, default=datetime.utcnow)
    )

    # Create all tables
    metadata.create_all(engine)

    print("✅ Database tables created successfully!")
    print("\n📋 Tables created:")
    print("   - users")
    print("   - capsules")
    print("   - payments")
    print("\n🎉 PostgreSQL database is ready to use!")

except Exception as e:
    print(f"❌ Error creating tables: {e}")
    exit(1)
