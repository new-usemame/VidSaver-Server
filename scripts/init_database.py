#!/usr/bin/env python3
"""Database Initialization Script

Initializes the SQLite database with the required schema and indexes.
Can be run standalone or imported by the main application.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import initialize_database, get_schema_version


def main():
    """Main initialization routine"""
    # Default database path
    db_path = Path(__file__).parent.parent / "data" / "downloads.db"
    
    # Allow override via command line argument
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    
    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Initializing database at: {db_path}")
    
    # Check if database already exists
    db_exists = db_path.exists()
    if db_exists:
        current_version = get_schema_version(str(db_path))
        print(f"Database already exists (schema version: {current_version})")
    else:
        print("Creating new database...")
    
    # Initialize database
    try:
        initialize_database(str(db_path))
        new_version = get_schema_version(str(db_path))
        print(f"✅ Database initialized successfully (schema version: {new_version})")
        
        # Show database info
        print(f"\nDatabase location: {db_path.absolute()}")
        print(f"Database size: {db_path.stat().st_size} bytes")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

