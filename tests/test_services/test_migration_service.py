"""Unit Tests for Migration Service

Tests database migration and rollback functionality.
"""

import pytest
import sqlite3

from app.services.migration_service import Migration, MigrationService
from app.models.database import initialize_database, get_schema_version


class TestMigration:
    """Test Migration class"""
    
    def test_migration_creation(self):
        """Test creating a migration"""
        migration = Migration(
            version=2,
            description="Test migration",
            up_sql=["ALTER TABLE downloads ADD COLUMN test TEXT"],
            down_sql=["ALTER TABLE downloads DROP COLUMN test"]
        )
        
        assert migration.version == 2
        assert migration.description == "Test migration"
        assert len(migration.up_sql) == 1
        assert len(migration.down_sql) == 1
    
    def test_migration_without_rollback(self):
        """Test migration without down_sql"""
        migration = Migration(
            version=2,
            description="Test migration",
            up_sql=["ALTER TABLE downloads ADD COLUMN test TEXT"]
        )
        
        assert migration.down_sql == []


class TestMigrationService:
    """Test MigrationService"""
    
    def test_get_current_version_fresh_db(self, temp_db_path):
        """Test getting version from fresh database"""
        # Initialize database
        initialize_database(temp_db_path)
        
        service = MigrationService(temp_db_path)
        version = service.get_current_version()
        
        assert version == 1  # Initial schema is v1
    
    def test_get_current_version_uninitialized(self, temp_db_path):
        """Test getting version from uninitialized database"""
        service = MigrationService(temp_db_path)
        version = service.get_current_version()
        
        assert version == 0
    
    def test_register_migration(self, temp_db_path):
        """Test registering migrations"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        migration = Migration(
            version=2,
            description="Add test field",
            up_sql=["ALTER TABLE downloads ADD COLUMN test_field TEXT"]
        )
        
        service.register_migration(migration)
        assert len(service.migrations) == 1
        assert service.migrations[0].version == 2
    
    def test_register_non_sequential_migration(self, temp_db_path):
        """Test that non-sequential migrations are rejected"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        migration1 = Migration(
            version=2,
            description="Migration 2",
            up_sql=["SELECT 1"]
        )
        service.register_migration(migration1)
        
        # Try to register v4 when we only have v2
        migration2 = Migration(
            version=4,
            description="Migration 4",
            up_sql=["SELECT 1"]
        )
        
        with pytest.raises(ValueError, match="sequential"):
            service.register_migration(migration2)
    
    def test_get_pending_migrations(self, temp_db_path):
        """Test getting pending migrations"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Register migrations
        for i in range(2, 5):
            migration = Migration(
                version=i,
                description=f"Migration {i}",
                up_sql=["SELECT 1"]
            )
            service.register_migration(migration)
        
        # All should be pending (current version is 1)
        pending = service.get_pending_migrations()
        assert len(pending) == 3
        assert [m.version for m in pending] == [2, 3, 4]
    
    def test_apply_migration(self, temp_db_path):
        """Test applying a migration"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Register migration that adds a column
        migration = Migration(
            version=2,
            description="Add progress field",
            up_sql=["ALTER TABLE downloads ADD COLUMN progress INTEGER DEFAULT 0"]
        )
        service.register_migration(migration)
        
        # Apply migration
        applied = service.migrate()
        assert applied == 1
        
        # Verify version updated
        assert service.get_current_version() == 2
        
        # Verify column was added
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(downloads)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "progress" in columns
        conn.close()
    
    def test_apply_multiple_migrations(self, temp_db_path):
        """Test applying multiple migrations"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Register multiple migrations
        migrations_data = [
            (2, "Add field1", "ALTER TABLE downloads ADD COLUMN field1 TEXT"),
            (3, "Add field2", "ALTER TABLE downloads ADD COLUMN field2 INTEGER"),
            (4, "Add field3", "ALTER TABLE downloads ADD COLUMN field3 REAL"),
        ]
        
        for version, desc, sql in migrations_data:
            migration = Migration(version=version, description=desc, up_sql=[sql])
            service.register_migration(migration)
        
        # Apply all migrations
        applied = service.migrate()
        assert applied == 3
        
        # Verify version
        assert service.get_current_version() == 4
        
        # Verify all columns were added
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(downloads)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "field1" in columns
        assert "field2" in columns
        assert "field3" in columns
        conn.close()
    
    def test_migrate_to_specific_version(self, temp_db_path):
        """Test migrating to a specific version"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Register 3 migrations
        for i in range(2, 5):
            migration = Migration(
                version=i,
                description=f"Migration {i}",
                up_sql=[f"ALTER TABLE downloads ADD COLUMN field{i} TEXT"]
            )
            service.register_migration(migration)
        
        # Migrate only to v3
        applied = service.migrate(target_version=3)
        assert applied == 2  # v2 and v3
        assert service.get_current_version() == 3
        
        # v4 should still be pending
        pending = service.get_pending_migrations()
        assert len(pending) == 1
        assert pending[0].version == 4
    
    def test_migrate_when_up_to_date(self, temp_db_path):
        """Test migrating when already up to date"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # No migrations registered
        applied = service.migrate()
        assert applied == 0
    
    def test_migration_rollback_on_error(self, temp_db_path):
        """Test that migration rolls back on error"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Register migration with invalid SQL
        migration = Migration(
            version=2,
            description="Bad migration",
            up_sql=[
                "ALTER TABLE downloads ADD COLUMN good_field TEXT",
                "THIS IS INVALID SQL",  # This will fail
            ]
        )
        service.register_migration(migration)
        
        # Attempt migration (should fail)
        with pytest.raises(sqlite3.OperationalError):
            service.migrate()
        
        # Verify version didn't change
        assert service.get_current_version() == 1
        
        # Verify column wasn't added (rollback worked)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(downloads)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "good_field" not in columns
        conn.close()
    
    def test_rollback_migration(self, temp_db_path):
        """Test rolling back a migration"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Note: SQLite doesn't support DROP COLUMN until version 3.35.0
        # So we'll use a table creation/deletion for rollback test
        migration = Migration(
            version=2,
            description="Add test table",
            up_sql=["CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)"],
            down_sql=["DROP TABLE test_table"]
        )
        service.register_migration(migration)
        
        # Apply migration
        service.migrate()
        assert service.get_current_version() == 2
        
        # Verify table exists
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        assert cursor.fetchone() is not None
        conn.close()
        
        # Rollback
        rolled_back = service.rollback(target_version=1)
        assert rolled_back == 1
        assert service.get_current_version() == 1
        
        # Verify table was dropped
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        assert cursor.fetchone() is None
        conn.close()
    
    def test_rollback_without_down_sql(self, temp_db_path):
        """Test that rollback fails if migration has no down_sql"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Migration without rollback SQL
        migration = Migration(
            version=2,
            description="No rollback",
            up_sql=["CREATE TABLE test_table (id INTEGER)"]
        )
        service.register_migration(migration)
        
        # Apply migration
        service.migrate()
        
        # Attempt rollback (should fail)
        with pytest.raises(ValueError, match="no rollback SQL"):
            service.rollback(target_version=1)
    
    def test_get_migration_history(self, temp_db_path):
        """Test retrieving migration history"""
        initialize_database(temp_db_path)
        service = MigrationService(temp_db_path)
        
        # Register and apply migrations
        for i in range(2, 4):
            migration = Migration(
                version=i,
                description=f"Migration {i}",
                up_sql=[f"CREATE TABLE test_table_{i} (id INTEGER)"],
                down_sql=[f"DROP TABLE test_table_{i}"]
            )
            service.register_migration(migration)
        
        service.migrate()
        
        # Get history
        history = service.get_migration_history()
        assert len(history) >= 2  # v1 (initial) + v2, v3
        
        # Check that our migrations are in history
        versions = [h[0] for h in history]
        assert 2 in versions
        assert 3 in versions
    
    def test_validate_migrations(self, temp_db_path):
        """Test migration validation"""
        initialize_database(temp_db_path)  # Initialize to v1
        service = MigrationService(temp_db_path)
        
        # Empty migrations list is valid
        assert service.validate_migrations() is True
        
        # Sequential migrations are valid (starting from v2, since v1 is current)
        for i in range(2, 5):
            migration = Migration(
                version=i,
                description=f"Migration {i}",
                up_sql=["SELECT 1"]
            )
            service.register_migration(migration)
        
        assert service.validate_migrations() is True
    
    def test_validate_migrations_with_gap(self, temp_db_path):
        """Test validation fails with version gap"""
        service = MigrationService(temp_db_path)
        
        # Add migration v2
        migration1 = Migration(version=2, description="M2", up_sql=["SELECT 1"])
        service.migrations.append(migration1)  # Bypass register to create gap
        
        # Add migration v4 (skipping v3)
        migration2 = Migration(version=4, description="M4", up_sql=["SELECT 1"])
        service.migrations.append(migration2)
        
        # Validation should fail
        assert service.validate_migrations() is False

