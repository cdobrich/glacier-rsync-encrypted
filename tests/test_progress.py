"""
Tests for progress bar functionality in glacier-rsync.
"""

import pytest
import os
from unittest.mock import patch
from .mocks.mock_glacier import MockGlacierClient
from src.backup_util import BackupUtil


def test_progress_bars_display(mock_args, temp_dir, capsys):
    """Test that progress bars are displayed during backup"""
    test_file = os.path.join(temp_dir, 'test.dat')
    with open(test_file, 'wb') as f:
        f.write(os.urandom(1024))
    
    mock_args.src = test_file
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            captured = capsys.readouterr()
            assert "Processing files" in captured.err
            assert "Uploading" in captured.err
        finally:
            backup_util.close()


def test_progress_bars_accuracy(mock_args, temp_dir, capsys):
    """Test that progress bars show correct progress"""
    test_file = os.path.join(temp_dir, 'test.dat')
    test_size = 1024 * 1024  # 1MB
    with open(test_file, 'wb') as f:
        f.write(os.urandom(test_size))
    
    mock_args.src = test_file
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            captured = capsys.readouterr()
            assert "1.05M" in captured.err  # tqdm formats 1MB as 1.05M
            assert "100%" in captured.err
        finally:
            backup_util.close()


def test_progress_bars_multiple_files(mock_args, temp_dir, capsys):
    """Test progress bars with multiple files"""
    test_files = []
    for i in range(3):
        path = os.path.join(temp_dir, f'test_file_{i}.dat')
        with open(path, 'wb') as f:
            f.write(os.urandom(1024))
        test_files.append(path)
    
    mock_args.src = temp_dir
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            captured = capsys.readouterr()
            assert "Processing files" in captured.err
            assert "100%" in captured.err
        finally:
            backup_util.close()


def test_progress_bars_large_file(mock_args, temp_dir, capsys):
    """Test progress bars with large file upload"""
    large_file = os.path.join(temp_dir, 'large_test_file.dat')
    file_size = mock_args.part_size * 2.5  # Create a file that needs multiple parts
    
    with open(large_file, 'wb') as f:
        f.write(os.urandom(int(file_size)))
    
    mock_args.src = large_file
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            captured = capsys.readouterr()
            assert "Uploading" in captured.err
            assert "2.62M" in captured.err  # tqdm formats 2.5MB as 2.62M
            assert "100%" in captured.err
        finally:
            backup_util.close()


def test_progress_bars_interruption(mock_args, temp_dir, capsys):
    """Test progress bars behavior on interruption"""
    test_file = os.path.join(temp_dir, 'test.dat')
    with open(test_file, 'wb') as f:
        f.write(os.urandom(1024 * 1024))
    
    mock_args.src = test_file
    
    with patch('boto3.client') as mock_boto3_client:
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        mock_glacier.create_vault(mock_args.vault)
        
        backup_util = BackupUtil(mock_args)
        try:
            # Force an interruption and capture the log output
            with patch('logging.info') as mock_logging:
                backup_util.stop()
                backup_util.backup()
                
                # Check if the logging call was made
                mock_logging.assert_any_call("Exiting early...")
        finally:
            backup_util.close()


@pytest.fixture(autouse=True)
def cleanup_test_env():
    """Clean up test environment before and after each test"""
    if os.path.exists("test.db"):
        os.remove("test.db")
    yield
    if os.path.exists("test.db"):
        os.remove("test.db")
