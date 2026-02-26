import os
import shutil
import logging
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

class AtomicFileSystem:
    """
    Handles atomic writes to the Sovereign Vault ensuring that no file 
    is ever corrupted during a write operation. It automatically creates
    history snapshots before overwriting existing files.
    """
    
    def __init__(self, vault_path: str = "/vault"):
        self.vault_path = vault_path
        self.history_path = os.path.join(vault_path, ".history")
        self._write_lock = Lock()
        
        # Ensure base directories exist
        os.makedirs(self.vault_path, exist_ok=True)
        os.makedirs(self.history_path, exist_ok=True)

    def _create_snapshot(self, filepath: str) -> None:
        """
        Creates a timestamped snapshot of a file in the .history directory.
        """
        if not os.path.exists(filepath):
            return
            
        try:
            # We want to maintain some structure in the history to know where it came from
            rel_path = os.path.relpath(filepath, self.vault_path)
            
            # Create a timestamped name: original_name.TIMESTAMP.ext
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            snapshot_filename = f"{name}.{timestamp}{ext}"
            
            # The destination path inside .history/
            snapshot_dir = os.path.join(self.history_path, os.path.dirname(rel_path))
            os.makedirs(snapshot_dir, exist_ok=True)
            snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
            
            shutil.copy2(filepath, snapshot_path)
            logger.info(f"Created atomic snapshot: {snapshot_path}")
            
        except Exception as e:
            logger.error(f"Failed to create snapshot for {filepath}: {e}")
            raise RuntimeError(f"Could not secure snapshot before write: {e}")

    def write_file(self, rel_path: str, content: str) -> str:
        """
        Safely writes content to `vault_path/rel_path` using a temporary file
        and os.replace for atomicity. Snaphots the old file if it exists.
        
        Returns the absolute path to the written file.
        """
        # Ensure path uses forward slashes in docker, but os.path.join handles it
        abs_dest_path = os.path.abspath(os.path.join(self.vault_path, rel_path))
        
        # Security check: Prevent directory traversal outside the vault
        if not abs_dest_path.startswith(os.path.abspath(self.vault_path)):
            raise ValueError("Path traversal detected. Cannot write outside the vault.")
            
        dest_dir = os.path.dirname(abs_dest_path)
        os.makedirs(dest_dir, exist_ok=True)
        
        # The temporary write path
        tmp_path = f"{abs_dest_path}.tmp.{datetime.utcnow().timestamp()}"
        
        with self._write_lock:
            # 1. Snapshot existing file (if any)
            self._create_snapshot(abs_dest_path)
            
            # 2. Write to a temporary file
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"Failed to write to temporary file {tmp_path}: {e}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
                
            # 3. Atomic replace (os.replace is atomic on POSIX systems)
            try:
                os.replace(tmp_path, abs_dest_path)
                logger.info(f"Atomically wrote: {abs_dest_path}")
            except Exception as e:
                logger.error(f"Failed to atomically replace {abs_dest_path}: {e}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
                
        return abs_dest_path

    def read_file(self, rel_path: str) -> str:
        """
        Reads a file from the vault.
        """
        abs_path = os.path.abspath(os.path.join(self.vault_path, rel_path))
        
        if not abs_path.startswith(os.path.abspath(self.vault_path)):
            raise ValueError("Path traversal detected.")
            
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found in vault: {rel_path}")
            
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()

# Singleton instance
atomic_fs = AtomicFileSystem()
