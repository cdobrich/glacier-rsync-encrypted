# tests/test_argparser.py
import pytest
from glacier_rsync.argparser import ArgParser
from unittest.mock import patch
import sys

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
        assert args.log_level == 'INFO'  # default value
        assert not args.compress  # default value

def test_compression_args():
    """Test compression argument parsing"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--compress', 'true',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.compress is True

def test_encryption_args():
    """Test encryption argument parsing"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--encrypt', 'true',
        '--encryption-key', 'test-key',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.encrypt is True
        assert args.encryption_key == 'test-key'

def test_encryption_missing_key():
    """Test encryption requires key"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--encrypt', 'true',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        with pytest.raises(SystemExit):
            ArgParser().get_args()

def test_log_level_args():
    """Test log level argument parsing"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--loglevel', 'DEBUG',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.log_level == 'DEBUG'

def test_invalid_log_level():
    """Test invalid log level handling"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--loglevel', 'INVALID',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        with pytest.raises(SystemExit):
            ArgParser().get_args()

def test_part_size_args():
    """Test part size argument parsing"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--part-size', '2097152',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.part_size == 2097152

def test_missing_required_args():
    """Test handling of missing required arguments"""
    test_args = ['prog', 'src_path']
    with patch('sys.argv', test_args):
        with pytest.raises(SystemExit):
            ArgParser().get_args()

def test_description_args():
    """Test description argument parsing"""
    test_args = [
        'prog',
        '--vault', 'test-vault',
        '--region', 'us-east-1',
        '--desc', 'test description',
        'src_path'
    ]
    with patch('sys.argv', test_args):
        args = ArgParser().get_args()
        assert args.desc == 'test description'

def test_boolean_conversion():
    """Test boolean argument conversion"""
    test_values = {
        'true': True,
        'yes': True,
        '1': True,
        'false': False,
        'no': False,
        '0': False
    }
    
    for value, expected in test_values.items():
        test_args = [
            'prog',
            '--vault', 'test-vault',
            '--region', 'us-east-1',
            '--compress', value,
            'src_path'
        ]
        with patch('sys.argv', test_args):
            args = ArgParser().get_args()
            assert args.compress == expected
