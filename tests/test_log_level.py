import pytest
import logging
from unittest.mock import patch, MagicMock
from src.argparser import ArgParser
import os
import sys

def test_default_log_level_info(mocker, tmp_path):
    """Test that the default log level is INFO."""
    sys.modules['src.progress'] = mocker.MagicMock()
    sys.modules['src.progress.ProgressPercentage'] = mocker.MagicMock()
    mock_args = MagicMock(log_level="INFO")

    with patch.object(ArgParser, 'get_args', return_value=mock_args):
        with patch('logging.basicConfig') as mock_basic_config:
            with patch('src.__main__.BackupUtil') as MockBackupUtil:
                mock_backup_util_instance = MockBackupUtil.return_value
                mock_backup_util_instance.backup.return_value = None
                import src.__main__
                src.__main__.main()
                mock_basic_config.assert_called_once()
                kwargs = mock_basic_config.call_args[1]
                assert kwargs['level'] == logging.INFO

def test_log_level_warning(mocker, tmp_path):
    """Test setting log level to WARNING."""
    sys.modules['src.progress'] = mocker.MagicMock()
    sys.modules['src.progress.ProgressPercentage'] = mocker.MagicMock()
    mock_args = MagicMock(log_level="WARNING")

    with patch.object(ArgParser, 'get_args', return_value=mock_args):
        with patch('logging.basicConfig') as mock_basic_config:
            with patch('src.__main__.BackupUtil') as MockBackupUtil:
                mock_backup_util_instance = MockBackupUtil.return_value
                mock_backup_util_instance.backup.return_value = None
                import src.__main__
                src.__main__.main()
                mock_basic_config.assert_called_once()
                kwargs = mock_basic_config.call_args[1]
                assert kwargs['level'] == logging.WARNING

def test_log_level_debug(mocker, tmp_path):
    """Test setting log level to DEBUG."""
    sys.modules['src.progress'] = mocker.MagicMock()
    sys.modules['src.progress.ProgressPercentage'] = mocker.MagicMock()
    mock_args = MagicMock(log_level="DEBUG")

    with patch.object(ArgParser, 'get_args', return_value=mock_args):
        with patch('logging.basicConfig') as mock_basic_config:
            with patch('src.__main__.BackupUtil') as MockBackupUtil:
                mock_backup_util_instance = MockBackupUtil.return_value
                mock_backup_util_instance.backup.return_value = None
                import src.__main__
                src.__main__.main()
                mock_basic_config.assert_called_once()
                kwargs = mock_basic_config.call_args[1]
                assert kwargs['level'] == logging.DEBUG

def test_invalid_log_level_handled(mocker, tmp_path):
    """Test that an invalid log level (passed via args) defaults to INFO."""
    sys.modules['src.progress'] = mocker.MagicMock()
    sys.modules['src.progress.ProgressPercentage'] = mocker.MagicMock()
    mock_args = MagicMock(log_level="INVALID")

    with patch.object(ArgParser, 'get_args', return_value=mock_args):
        with patch('logging.basicConfig') as mock_basic_config:
            with patch('src.__main__.BackupUtil') as MockBackupUtil:
                mock_backup_util_instance = MockBackupUtil.return_value
                mock_backup_util_instance.backup.return_value = None
                import src.__main__
                src.__main__.main()
                mock_basic_config.assert_called_once()
                kwargs = mock_basic_config.call_args[1]
                assert kwargs['level'] == logging.INFO # Final assertion for invalid level
