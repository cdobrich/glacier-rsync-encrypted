"""
Integration tests for glacier-rsync.
Tests complete backup cycles and incremental backups.
"""

import pytest
import os
from unittest.mock import patch
from cryptography.fernet import Fernet
from .mocks.mock_glacier import MockGlacierClient
from glacier_rsync.backup_util import BackupUtil


@pytest.mark.integration
def test_full_backup_cycle(mock_args, temp_dir):
    """Test a complete backup cycle with multiple files"""
    # Create test files
    test_files = []
    for i in range(3):
        path = os.path.join(temp_dir, f'test_file_{i}.dat')
        with open(path, 'wb') as f:
            f.write(os.urandom(1024 * (i + 1)))
        test_files.append(path)
    
    mock_args.src = temp_dir
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        
        # Create vault
        mock_glacier.create_vault(mock_args.vault)
        
        # Run backup
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            # Verify all files were processed
            cur = backup_util.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sync_history")
            count = cur.fetchone()[0]
            assert count == len(test_files), "Not all files were processed"
            
            # Verify archive creation
            for file in test_files:
                cur.execute("SELECT archive_id FROM sync_history WHERE path = ?", (file,))
                archive_id = cur.fetchone()[0]
                assert f"archive-upload-" in archive_id
            
            cur.close()
        finally:
            backup_util.close()


@pytest.mark.integration
def test_incremental_backup(mock_args, temp_dir):
    """Test that only new or modified files are backed up"""
    # Initial file
    initial_file = os.path.join(temp_dir, 'initial.dat')
    with open(initial_file, 'wb') as f:
        f.write(os.urandom(1024))
    
    mock_args.src = temp_dir
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        # First backup
        backup_util = BackupUtil(mock_args)
        backup_util.backup()
        backup_util.close()
        
        # Create new file
        new_file = os.path.join(temp_dir, 'new.dat')
        with open(new_file, 'wb') as f:
            f.write(os.urandom(1024))
        
        # Second backup
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            # Verify only new file was processed
            cur = backup_util.conn.cursor()
            cur.execute("SELECT path FROM sync_history ORDER BY id DESC LIMIT 1")
            last_backed_up = cur.fetchone()[0]
            assert last_backed_up == new_file
            cur.close()
        finally:
            backup_util.close()


@pytest.mark.integration
def test_modified_file_backup(mock_args, temp_dir):
    """Test that modified files are re-backed up"""
    # Initial file
    test_file = os.path.join(temp_dir, 'test.dat')
    with open(test_file, 'wb') as f:
        f.write(os.urandom(1024))
    
    mock_args.src = temp_dir
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        # First backup
        backup_util = BackupUtil(mock_args)
        backup_util.backup()
        backup_util.close()
        
        # Modify file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024))
        
        # Second backup
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            # Verify file was backed up again
            cur = backup_util.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sync_history WHERE path = ?", (test_file,))
            count = cur.fetchone()[0]
            assert count == 2, "Modified file was not re-backed up"
            cur.close()
        finally:
            backup_util.close()


@pytest.mark.integration
def test_compression_and_encryption(mock_args, temp_dir):
    """Test backup with both compression and encryption enabled"""
    test_file = os.path.join(temp_dir, 'test.dat')
    with open(test_file, 'wb') as f:
        f.write(os.urandom(1024 * 1024))  # 1MB file
    
    mock_args.src = temp_dir
    mock_args.compress = True
    mock_args.encrypt = True
    mock_args.encryption_key = Fernet.generate_key().decode()
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            # Verify compression and encryption flags
            cur = backup_util.conn.cursor()
            cur.execute("SELECT compression FROM sync_history WHERE path = ?", (test_file,))
            compression = cur.fetchone()[0]
            assert "encrypted" in compression
            assert "zstd" in compression
            cur.close()
        finally:
            backup_util.close()


@pytest.mark.integration
def test_empty_directory(mock_args, temp_dir):
    """Test handling of empty directories"""
    mock_args.src = temp_dir
    
    # Remove any existing database
    if os.path.exists(mock_args.db):
        os.remove(mock_args.db)
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            # Verify no entries in sync history
            cur = backup_util.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sync_history")
            count = cur.fetchone()[0]
            assert count == 0, "Empty directory should not create any entries"
            cur.close()
        finally:
            backup_util.close()


@pytest.mark.integration
def test_backup_interruption(mock_args, temp_dir):
    """Test graceful handling of backup interruption"""
    # Create multiple files
    test_files = []
    for i in range(5):
        path = os.path.join(temp_dir, f'test_file_{i}.dat')
        with open(path, 'wb') as f:
            f.write(os.urandom(1024 * 1024))  # 1MB each
        test_files.append(path)
    
    mock_args.src = temp_dir
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            # Set up interruption after processing some files
            def interrupt_after_files(file_path):
                if 'test_file_2.dat' in file_path:
                    backup_util.stop()
            
            # Patch the _compress method to trigger interruption
            original_compress = backup_util._compress
            def mock_compress(file_path):
                interrupt_after_files(file_path)
                return original_compress(file_path)
            
            backup_util._compress = mock_compress
            
            # Run backup
            backup_util.backup()
            
            # Verify partial backup
            cur = backup_util.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sync_history")
            count = cur.fetchone()[0]
            assert count < len(test_files), "Interruption was not handled"
            cur.close()
        finally:
            backup_util.close()


@pytest.fixture(autouse=True)
def cleanup_test_env():
    """Clean up test environment before and after each test"""
    # Pre-test cleanup
    if os.path.exists("test.db"):
        os.remove("test.db")
    
    yield
    
    # Post-test cleanup
    if os.path.exists("test.db"):
        os.remove("test.db")
