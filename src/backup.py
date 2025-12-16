"""
Database backup system for Notion data
Automatically exports and stores Notion database contents
"""
import json
from datetime import datetime
from pathlib import Path

from .logger import logger


class NotionBackup:
    """
    Backup Notion databases to local JSON files.
    
    Works with our custom NotionClient (not the official SDK).
    """

    def __init__(self, backup_dir: str = "backups"):
        """
        Initialize backup system
        
        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Create backup directory with proper permissions."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            # Ensure we can write to it
            test_file = self.backup_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            logger.info("backup.dir_ready", path=str(self.backup_dir))
        except Exception as e:
            logger.error("backup.dir_failed", path=str(self.backup_dir), error=str(e))
            # Fallback to /tmp
            self.backup_dir = Path("/tmp/telegram-screener-backups")
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            logger.warning("backup.dir_fallback", path=str(self.backup_dir))

    def backup_database(self, notion_client, database_id: str, database_name: str) -> str | None:
        """
        Backup a Notion database to JSON file using our NotionClient.
        
        Args:
            notion_client: Our NotionClient instance (not official SDK)
            database_id: Notion database ID
            database_name: Human-readable name for the database
            
        Returns:
            Path to backup file, or None if failed
        """
        if not database_id or database_id.startswith("LOADED_FROM"):
            logger.warning("backup.skipped_invalid_id", database=database_name)
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{database_name}_{timestamp}.json"
        filepath = self.backup_dir / filename

        try:
            logger.info("backup.started", database=database_name, id=database_id[:8])

            # Use our NotionClient's query method
            results = self._query_all_pages(notion_client, database_id)

            if results is None:
                logger.error("backup.query_failed", database=database_name)
                return None

            # Save to file
            backup_data = {
                "database_name": database_name,
                "database_id": database_id,
                "timestamp": timestamp,
                "backed_up_at": datetime.now().isoformat(),
                "page_count": len(results),
                "pages": results
            }

            # Atomic write
            temp_file = filepath.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str)
            temp_file.rename(filepath)

            logger.info("backup.completed",
                       database=database_name,
                       pages=len(results),
                       file=str(filepath),
                       size_kb=filepath.stat().st_size // 1024)

            return str(filepath)

        except Exception as e:
            logger.error("backup.failed", database=database_name, error=str(e))
            return None

    def _query_all_pages(self, notion_client, database_id: str) -> list[dict] | None:
        """
        Query all pages from a Notion database using pagination.
        
        Args:
            notion_client: Our NotionClient instance
            database_id: Notion database ID
            
        Returns:
            List of all pages, or None if failed
        """

        results = []
        has_more = True
        start_cursor = None

        try:
            while has_more:
                url = f"{notion_client.base_url}/databases/{database_id}/query"

                payload = {}
                if start_cursor:
                    payload["start_cursor"] = start_cursor

                response = notion_client._request("post", url, json=payload)

                if response.status_code != 200:
                    logger.error("backup.query_error",
                               status=response.status_code,
                               error=response.text[:100])
                    return None

                data = response.json()
                results.extend(data.get("results", []))
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

                logger.debug("backup.page_fetched",
                           count=len(data.get("results", [])),
                           total=len(results),
                           has_more=has_more)

            return results

        except Exception as e:
            logger.error("backup.pagination_error", error=str(e))
            return None

    def backup_all(self, notion_client, databases: dict[str, str]) -> list[str]:
        """
        Backup multiple databases
        
        Args:
            notion_client: NotionClient instance
            databases: Dictionary of {name: database_id}
            
        Returns:
            List of successful backup file paths
        """
        backup_files = []
        failed = []

        for name, db_id in databases.items():
            if db_id and not db_id.startswith("LOADED_FROM"):
                filepath = self.backup_database(notion_client, db_id, name)
                if filepath:
                    backup_files.append(filepath)
                    print(f"   ✅ Backed up {name}: {filepath}")
                else:
                    failed.append(name)
                    print(f"   ⚠️  Failed to backup {name}")

        logger.info("backup.all_completed",
                   success=len(backup_files),
                   failed=len(failed))

        return backup_files

        return backup_files

    def cleanup_old_backups(self, days: int = 30) -> int:
        """
        Remove backup files older than specified days
        
        Args:
            days: Keep backups newer than this many days
            
        Returns:
            Number of files deleted
        """
        deleted = 0
        cutoff_time = datetime.now().timestamp() - (days * 86400)

        try:
            for filepath in self.backup_dir.glob("*.json"):
                if filepath.stat().st_mtime < cutoff_time:
                    filepath.unlink()
                    deleted += 1
                    logger.info("backup_deleted", file=str(filepath))

            if deleted > 0:
                logger.info("backup_cleanup", deleted=deleted, days=days)

        except Exception as e:
            logger.error("backup_cleanup_failed", error=str(e))

        return deleted

    def restore_database(self, backup_file: str) -> dict:
        """
        Load backup file and return data
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            Backup data dictionary
        """
        try:
            with open(backup_file) as f:
                data = json.load(f)

            logger.info("backup_loaded",
                       file=backup_file,
                       pages=data.get("page_count", 0))

            return data

        except Exception as e:
            logger.error("backup_load_failed", file=backup_file, error=str(e))
            raise

    def get_latest_backup(self, database_name: str) -> str | None:
        """
        Get the most recent backup file for a database
        
        Args:
            database_name: Name of the database
            
        Returns:
            Path to latest backup file, or None if not found
        """
        pattern = f"{database_name}_*.json"
        files = sorted(self.backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        if files:
            return str(files[0])
        return None

    def get_backup_stats(self) -> dict:
        """
        Get statistics about stored backups
        
        Returns:
            Dictionary with backup statistics
        """
        backup_files = list(self.backup_dir.glob("*.json"))

        total_size = sum(f.stat().st_size for f in backup_files)

        # Group by database name
        databases = {}
        for filepath in backup_files:
            db_name = filepath.stem.rsplit('_', 2)[0]  # Extract name before timestamp
            if db_name not in databases:
                databases[db_name] = 0
            databases[db_name] += 1

        return {
            "total_backups": len(backup_files),
            "total_size_mb": total_size / (1024 * 1024),
            "databases": databases,
            "backup_dir": str(self.backup_dir)
        }
