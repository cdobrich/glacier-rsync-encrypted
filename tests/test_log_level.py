import pytest
import logging
import sys
from unittest.mock import patch, MagicMock
from src import __main__
from src.argparser import ArgParser
import argparse
import os

def test_default_log_level_info(mocker, tmp_path):
    """Test that the default log level is INFO."""

    # Create a mock args object instead of relying on CLI args
    mock_args = MagicMock()
    mock_args.log_level = "INFO"
    mock_args.src = tmp_path  # Provide a dummy src
    mock_args.vault = "test-vault"
    mock_args.region = "us-east-1"
    mock_args.list_incomplete_uploads = False
    mock_args.abort_incomplete_uploads = False

    mocker.patch('src.argparser.ArgParser.get_args', return_value=mock_args)
    with patch('logging.basicConfig') as mock_basic_config:
        with patch('src.__main__.BackupUtil') as MockBackupUtil:
            mock_backup_util_instance = MockBackupUtil.return_value
            mock_backup_util_instance.backup.return_value = None
            __main__.main()
            mock_basic_config.assert_called_once()
            kwargs = mock_basic_config.call_args[1]
            assert kwargs['level'] == logging.INFO

def test_log_level_warning(mocker, tmp_path):
    """Test setting log level to WARNING."""

    # Create a mock args object
    mock_args = MagicMock()
    mock_args.log_level = "WARNING"
    mock_args.src = tmp_path  # Provide a dummy src
    mock_args.vault = "test-vault"
    mock_args.region = "us-east-1"
    mock_args.list_incomplete_uploads = False
    mock_args.abort_incomplete_uploads = False

    mocker.patch('src.argparser.ArgParser.get_args', return_value=mock_args)
    with patch('logging.basicConfig') as mock_basic_config:
        with patch('src.__main__.BackupUtil') as MockBackupUtil:
            mock_backup_util_instance = MockBackupUtil.return_value
            mock_backup_util_instance.backup.return_value = None
            __main__.main()
            mock_basic_config.assert_called_once()
            kwargs = mock_basic_config.call_args[1]
            assert kwargs['level'] == logging.WARNING

def test_log_level_debug(mocker, tmp_path):
    """Test setting log level to DEBUG."""

    # Create a mock args object
    mock_args = MagicMock()
    mock_args.log_level = "DEBUG"
    mock_args.src = tmp_path  # Provide a dummy src
    mock_args.vault = "test-vault"
    mock_args.region = "us-east-1"
    mock_args.list_incomplete_uploads = False
    mock_args.abort_incomplete_uploads = False

    mocker.patch('src.argparser.ArgParser.get_args', return_value=mock_args)
    with patch('logging.basicConfig') as mock_basic_config:
        with patch('src.__main__.BackupUtil') as MockBackupUtil:
            mock_backup_util_instance = MockBackupUtil.return_value
            mock_backup_util_instance.backup.return_value = None
            __main__.main()
            mock_basic_config.assert_called_once()
            kwargs = mock_basic_config.call_args[1]
            assert kwargs['level'] == logging.DEBUG

def test_invalid_log_level_handled(mocker, tmp_path):
    """Test that an invalid log level (passed via args) defaults to INFO."""

    # Create a mock args object
    mock_args = MagicMock()
    mock_args.log_level = "INVALID"
    mock_args.src = tmp_path  # Provide a dummy src
    mock_args.vault = "test-vault"
    mock_args.region = "us-east-1"
    mock_args.list_incomplete_uploads = False
    mock_args.abort_incomplete_uploads = False

    mocker.patch('src.argparser.ArgParser.get_args', return_value=mock_args)
    with patch('logging.basicConfig') as mock_basic_config:
        with patch('src.__main__.BackupUtil') as MockBackupUtil:
            mock_backup_util_instance = MockBackupUtil.return_value
            mock_backup_util_instance.backup.return_value = None
            __main__.main()
            mock_basic_config.assert_called_once()
            kwargs = mock_basic_config.call_args[1]
            assert kwargs['level'] == logging.INFO
