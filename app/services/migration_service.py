"""Database Migration Service

Handles database schema versioning and migrations for future schema changes.
Implements migration tracking and execution with rollback support.
"""

import sqlite3
from typing import List, Callable, Tuple
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration"""
    
    def __init__(
        self,
        version: int,
        description: str,
        up_sql: List[str],
        down_sql: List[str] = None
    ):
        """Initialize migration
        
        Args:
            version: Migration version number (must be sequential)
            description: Human-readable description
            up_sql: List of SQL statements to apply migration
            down_sql: Optional list of SQL statements to rollback migration
        """
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql or []
    
    def apply(self, conn: sqlite3.Connection):
        """Apply migration (execute up_sql)
        
        Args:
            conn: Database connection
            
        Raises:
            sqlite3.Error: On SQL execution errors
        """
        cursor = conn.cursor()
        for sql in self.up_sql:
            logger.info(f"Executing migration {self.version}: {sql[:50]}...")
            cursor.execute(sql)
    
    def rollback(self, conn: sqlite3.Connection):
        """Rollback migration (execute down_sql)
        
        Args:
            conn: Database connection
            
        Raises:
            sqlite3.Error: On SQL execution errors
        """
        if not self.down_sql:
            raise ValueError(f"Migration {self.version} has no rollback SQL")
        
        cursor = conn.cursor()
        for sql in self.down_sql:
            logger.info(f"Rolling back migration {self.version}: {sql[:50]}...")
            cursor.execute(sql)


class MigrationService:
    """Service for managing database migrations"""
    
    def __init__(self, db_path: str):
        """Initialize migration service
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.migrations: List[Migration] = []
    
    def register_migration(self, migration: Migration):
        """Register a migration
        
        Args:
            migration: Migration to register
        """
        # Validate version is sequential
        if self.migrations:
            last_version = self.migrations[-1].version
            if migration.version != last_version + 1:
                raise ValueError(
                    f"Migration version must be sequential. "
                    f"Expected {last_version + 1}, got {migration.version}"
                )
        
        self.migrations.append(migration)
        logger.info(f"Registered migration v{migration.version}: {migration.description}")
    
    def get_current_version(self) -> int:
        """Get current database schema version
        
        Returns:
            Current version number, or 0 if not initialized
        """
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(version) FROM schema_migrations")
                result = cursor.fetchone()
                return result[0] if result and result[0] is not None else 0
            finally:
                conn.close()
        except sqlite3.OperationalError:
            # Table doesn't exist
            return 0
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get migrations that haven't been applied yet
        
        Returns:
            List of pending migrations
        """
        current_version = self.get_current_version()
        return [m for m in self.migrations if m.version > current_version]
    
    def _backup_database(self) -> str:
        """Create a backup of the database before migrations
        
        Returns:
            Path to backup file
            
        Raises:
            Exception: If backup fails
        """
        import shutil
        from pathlib import Path
        
        db_path = Path(self.db_path)
        
        # Create backups directory
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
        backup_path = backup_dir / backup_filename
        
        # Copy database file
        logger.info(f"Creating database backup: {backup_path}")
        shutil.copy2(self.db_path, backup_path)
        
        # Clean up old backups (keep last 5)
        self._cleanup_old_backups(backup_dir, db_path.stem, keep=5)
        
        logger.info(f"Database backup created successfully: {backup_path}")
        return str(backup_path)
    
    def _cleanup_old_backups(self, backup_dir: Path, db_stem: str, keep: int = 5):
        """Clean up old backup files, keeping only the most recent ones
        
        Args:
            backup_dir: Directory containing backups
            db_stem: Database filename stem (without extension)
            keep: Number of backups to keep
        """
        # Find all backup files for this database
        backup_pattern = f"{db_stem}_backup_*"
        backups = sorted(backup_dir.glob(backup_pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Delete old backups
        if len(backups) > keep:
            for old_backup in backups[keep:]:
                try:
                    old_backup.unlink()
                    logger.info(f"Deleted old backup: {old_backup}")
                except Exception as e:
                    logger.warning(f"Failed to delete old backup {old_backup}: {e}")
    
    def migrate(self, target_version: int = None) -> int:
        """Apply pending migrations up to target version
        
        Args:
            target_version: Version to migrate to (None = latest)
            
        Returns:
            Number of migrations applied
            
        Raises:
            sqlite3.Error: On migration errors
        """
        current_version = self.get_current_version()
        
        if target_version is None:
            target_version = self.migrations[-1].version if self.migrations else current_version
        
        if target_version < current_version:
            raise ValueError(
                f"Target version {target_version} is less than current version {current_version}. "
                f"Use rollback() instead."
            )
        
        pending = [m for m in self.migrations if current_version < m.version <= target_version]
        
        if not pending:
            logger.info(f"Database is up to date at version {current_version}")
            return 0
        
        # Create backup before applying migrations
        try:
            backup_path = self._backup_database()
            logger.info(f"✅ Database backup created: {backup_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create database backup: {e}")
            logger.warning("Continuing with migration without backup (not recommended)")
        
        conn = sqlite3.connect(self.db_path)
        applied_count = 0
        
        try:
            for migration in pending:
                logger.info(
                    f"Applying migration v{migration.version}: {migration.description}"
                )
                
                # Begin transaction
                conn.execute("BEGIN")
                
                try:
                    # Apply migration
                    migration.apply(conn)
                    
                    # Record migration
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                        (migration.version, int(datetime.now().timestamp()), migration.description)
                    )
                    
                    conn.commit()
                    applied_count += 1
                    logger.info(f"Migration v{migration.version} applied successfully")
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Migration v{migration.version} failed: {e}")
                    raise
            
            logger.info(f"Applied {applied_count} migration(s)")
            return applied_count
            
        finally:
            conn.close()
    
    def rollback(self, target_version: int) -> int:
        """Rollback migrations to target version
        
        Args:
            target_version: Version to rollback to
            
        Returns:
            Number of migrations rolled back
            
        Raises:
            sqlite3.Error: On rollback errors
        """
        current_version = self.get_current_version()
        
        if target_version >= current_version:
            logger.info(f"Already at or before version {target_version}")
            return 0
        
        # Get migrations to rollback (in reverse order)
        to_rollback = [
            m for m in reversed(self.migrations) 
            if target_version < m.version <= current_version
        ]
        
        if not to_rollback:
            logger.warning(f"No migrations found to rollback to version {target_version}")
            return 0
        
        conn = sqlite3.connect(self.db_path)
        rolled_back_count = 0
        
        try:
            for migration in to_rollback:
                logger.info(
                    f"Rolling back migration v{migration.version}: {migration.description}"
                )
                
                # Begin transaction
                conn.execute("BEGIN")
                
                try:
                    # Rollback migration
                    migration.rollback(conn)
                    
                    # Remove migration record
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM schema_migrations WHERE version = ?",
                        (migration.version,)
                    )
                    
                    conn.commit()
                    rolled_back_count += 1
                    logger.info(f"Migration v{migration.version} rolled back successfully")
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Rollback of v{migration.version} failed: {e}")
                    raise
            
            logger.info(f"Rolled back {rolled_back_count} migration(s)")
            return rolled_back_count
            
        finally:
            conn.close()
    
    def get_migration_history(self) -> List[Tuple[int, int, str]]:
        """Get history of applied migrations
        
        Returns:
            List of tuples: (version, applied_at, description)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT version, applied_at, description FROM schema_migrations ORDER BY version"
                )
                return cursor.fetchall()
            finally:
                conn.close()
        except sqlite3.OperationalError:
            return []
    
    def validate_migrations(self) -> bool:
        """Validate that migrations are sequential and have no gaps
        
        Returns:
            True if valid, False otherwise
        """
        if not self.migrations:
            return True
        
        # Migrations should start from current_version + 1
        current_version = self.get_current_version()
        expected_version = current_version + 1
        
        for migration in self.migrations:
            if migration.version != expected_version:
                logger.error(
                    f"Migration version mismatch: expected v{expected_version}, got v{migration.version}"
                )
                return False
            expected_version += 1
        
        return True


# Migration v2: Add multi-user support with genre-based organization
MIGRATION_V2_MULTI_USER = Migration(
    version=2,
    description="Add users table and multi-user support with genre detection",
    up_sql=[
        # Create users table
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at INTEGER NOT NULL
        )
        """,
        # Create index on username
        "CREATE INDEX IF NOT EXISTS idx_username ON users(username COLLATE NOCASE)",
        
        # Create default user for existing downloads
        """
        INSERT INTO users (username, created_at)
        VALUES ('default', strftime('%s', 'now'))
        """,
        
        # Create new downloads table with new schema
        """
        CREATE TABLE downloads_new (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            client_id TEXT NOT NULL,
            status TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            genre TEXT NOT NULL,
            filename TEXT,
            file_path TEXT,
            file_size INTEGER,
            error_message TEXT,
            genre_detection_error TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            started_at INTEGER,
            completed_at INTEGER,
            last_updated INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        
        # Copy existing data to new table (assign to default user with 'unknown' genre)
        """
        INSERT INTO downloads_new (
            id, url, client_id, status, user_id, genre,
            filename, file_path, file_size, error_message, genre_detection_error,
            retry_count, created_at, started_at, completed_at, last_updated
        )
        SELECT 
            id, url, client_id, status, 
            (SELECT id FROM users WHERE username = 'default'),
            'unknown',
            filename, file_path, file_size, error_message, NULL,
            retry_count, created_at, started_at, completed_at, last_updated
        FROM downloads
        """,
        
        # Drop old table
        "DROP TABLE downloads",
        
        # Rename new table
        "ALTER TABLE downloads_new RENAME TO downloads",
        
        # Recreate indexes
        "CREATE INDEX IF NOT EXISTS idx_status ON downloads(status)",
        "CREATE INDEX IF NOT EXISTS idx_created_at ON downloads(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_client_id ON downloads(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_id ON downloads(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_genre ON downloads(genre)",
    ],
    down_sql=[
        # This is complex and destructive, so we won't support rollback
        # In production, take backups before migrating
    ]
)


def get_migration_service(db_path: str) -> MigrationService:
    """Get a configured migration service with all migrations registered
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        MigrationService with all migrations registered
    """
    service = MigrationService(db_path)
    service.register_migration(MIGRATION_V2_MULTI_USER)
    return service

