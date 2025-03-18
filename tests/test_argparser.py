# tests/test_argparser.py
import pytest
from src.argparser import ArgParser
from unittest.mock import patch
import sys
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode
import os

def test_basic_args():
    """Test basic argument parsing"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--db', 'test.db',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.vault == 'test-vault'
        assert args.region == 'us-east-1'
        assert args.db == 'test.db'
        assert args.src == 'src_path'

def test_encryption_args():
    """Test encryption argument parsing with generated key"""
    # Generate and verify a valid Fernet key
    key = Fernet.generate_key()
    valid_key = key.decode()
    
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--encrypt', 'true',
        '--encryption-key', valid_key,
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.encrypt is True
        assert args.encryption_key == valid_key

def test_user_provided_encryption_key():
    """Test encryption with various user-provided keys"""
    # Test cases for user-provided keys
    test_cases = [
        # Valid cases
        (urlsafe_b64encode(os.urandom(32)).decode(), True),  # Valid 32-byte random key
        (Fernet.generate_key().decode(), True),              # Valid generated key
        
        # Invalid cases
        ("too-short-key", False),                           # Too short
        ("A" * 44, False),                                  # Wrong format
        ("not-base64-encoded@#$", False),                   # Not base64
        ("", False),                                        # Empty
        (None, False),                                      # None
    ]

    for key, should_pass in test_cases:
        test_args = [
            'prog',
            '--vault', 'test-vault',
            '--region', 'us-east-1',
            '--encrypt', 'true',
            '--encryption-key', key if key is not None else '',
            'src_path'
        ]
        
        with patch('sys.argv', test_args):
            if should_pass:
                # Should pass validation
                args = ArgParser().get_args()
                assert args.encrypt is True
                assert args.encryption_key == key
            else:
                # Should fail validation
                with pytest.raises(SystemExit):
                    ArgParser().get_args()

def test_encryption_key_file(tmp_path):
    """Test encryption key file handling"""
    # Generate and verify a valid Fernet key
    key = Fernet.generate_key()
    valid_key = key.decode()
    
    # Create temporary key file
    key_file = tmp_path / "test.key"
    key_file.write_text(valid_key)
    
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--encrypt', 'true',
        '--encryption-key-file', str(key_file),
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.encrypt is True
        assert args.encryption_key == valid_key

def test_invalid_key_file_content(tmp_path):
    """Test handling of key files with invalid content"""
    invalid_keys = [
        "not-a-valid-key",
        "A" * 44,
        "",
        "not-base64@#$"
    ]

    for invalid_key in invalid_keys:
        key_file = tmp_path / "invalid.key"
        key_file.write_text(invalid_key)
        
        test_args = [
            'prog',
            '--vault', 'test-vault',
            '--region', 'us-east-1',
            '--encrypt', 'true',
            '--encryption-key-file', str(key_file),
            'src_path'
        ]
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                ArgParser().get_args()

def test_encryption_key_requirements():
    """Test specific encryption key requirements"""
    # Test key length requirements
    for length in [16, 24, 31, 33, 64]:  # Various invalid lengths
        invalid_key = urlsafe_b64encode(os.urandom(length)).decode()
        test_args = [
            'prog',
            '--vault', 'test-vault',
            '--region', 'us-east-1',
            '--encrypt', 'true',
            '--encryption-key', invalid_key,
            'src_path'
        ]
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                ArgParser().get_args()

def test_encryption_missing_key():
    """Test encryption requires key"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--encrypt', 'true',
        'src_path'
    ]
    with pytest.raises(SystemExit):
        with patch('sys.argv', test_args):
            ArgParser().get_args()

def test_both_key_options():
    """Test that providing both key options raises error"""
    valid_key = Fernet.generate_key().decode()
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--encrypt', 'true',
        '--encryption-key', valid_key,
        '--encryption-key-file', 'some_file.key',
        'src_path'
    ]
    with pytest.raises(SystemExit):
        with patch('sys.argv', test_args):
            ArgParser().get_args()
