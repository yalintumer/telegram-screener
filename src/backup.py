"""
Database backup system for Notion data
Automatically exports and stores Notion database contents
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from .logger import logger


class NotionBackup:
    """Backup Notion databases to local JSON files"""
    
    def __init__(self, backup_dir: str = "backups"):
        """
        Initialize backup system
        
        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    def backup_database(self, notion_client, database_id: str, database_name: str) -> str:
        """
        Backup a Notion database to JSON file
        
        Args:
            notion_client: NotionClient instance
            database_id: Notion database ID
            database_name: Human-readable name for the database
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{database_name}_{timestamp}.json"
        filepath = self.backup_dir / filename
        
        try:
            logger.info("backup_started", database=database_name, id=database_id)
            
            # Query all pages from database
            results = []
            has_more = True
            start_cursor = None
            
            while has_more:
                response = notion_client.client.databases.query(
                    database_id=database_id,
                    start_cursor=start_cursor
                )
                
                results.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            # Save to file
            backup_data = {
                "database_name": database_name,
                "database_id": database_id,
                "timestamp": timestamp,
                "page_count": len(results),
                "pages": results
            }
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info("backup_completed", 
                       database=database_name,
                       pages=len(results),
                       file=str(filepath))
            
            return str(filepath)
            
        except Exception as e:
            logger.error("backup_failed", database=database_name, error=str(e))
            raise
    
    def backup_all(self, notion_client, databases: Dict[str, str]) -> List[str]:
        """
        Backup multiple databases
        
        Args:
            notion_client: NotionClient instance
            databases: Dictionary of {name: database_id}
            
        Returns:
            List of backup file paths
        """
        backup_files = []
        
        for name, db_id in databases.items():
            if db_id:  # Only backup if database ID is configured
                try:
                    filepath = self.backup_database(notion_client, db_id, name)
                    backup_files.append(filepath)
                    print(f"   ✅ Backed up {name}: {filepath}")
                except Exception as e:
                    print(f"   ⚠️  Failed to backup {name}: {e}")
        
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
            with open(backup_file, 'r') as f:
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
