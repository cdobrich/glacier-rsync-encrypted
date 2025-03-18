
# tests/test_backup_util.py
import pytest
from src.backup_util import BackupUtil
from unittest.mock import patch
import os

def test_db_initialization(mock_args, temp_dir):
    mock_args.src = temp_dir
    backup_util = BackupUtil(mock_args)
    assert os.path.exists(mock_args.db)
    
    cur = backup_util.conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_history'")
    assert cur.fetchone() is not None
    cur.close()

