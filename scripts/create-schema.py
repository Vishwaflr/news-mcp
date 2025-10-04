#!/usr/bin/env python3
"""Create database schema from SQLModel definitions."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import create_db_and_tables
from app import models  # Import all models to register them

if __name__ == "__main__":
    print("Creating all tables from SQLModel definitions...")
    create_db_and_tables()
    print("✓ Schema created successfully!")
