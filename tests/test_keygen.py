 
# tests/test_keygen.py
import pytest
import os
from src.keygen import generate_key_file, validate_key
from cryptography.fernet import Fernet
import stat


def test_generate_key_file(tmp_path):
    """Test basic key file generation"""
    key_file = tmp_path / "test.key"
    generate_key_file(str(key_file))
    
    # Check file exists
    assert key_file.exists()
    
    # Check file permissions (600)
    mode = os.stat(key_file).st_mode
    assert mode & stat.S_IRUSR  # Owner can read
    assert mode & stat.S_IWUSR  # Owner can write
    assert not mode & stat.S_IRWXG  # Group has no permissions
    assert not mode & stat.S_IRWXO  # Others have no permissions
    
    # Check key content is valid
    with open(key_file, 'rb') as f:
        key = f.read()
    is_valid, _ = validate_key(key)
    assert is_valid


def test_force_overwrite(tmp_path):
    """Test force overwrite of existing key file"""
    key_file = tmp_path / "test.key"
    
    # Create initial key
    generate_key_file(str(key_file))
    with open(key_file, 'rb') as f:
        original_key = f.read()
    
    # Try to generate new key without force
    with pytest.raises(FileExistsError):
        generate_key_file(str(key_file))
    
    # Generate new key with force
    generate_key_file(str(key_file), force=True)
    
    # Check key has changed
    with open(key_file, 'rb') as f:
        new_key = f.read()
    assert new_key != original_key


def test_key_validation():
    """Test key validation function"""
    test_cases = [
        # Valid cases
        (Fernet.generate_key(), True),
        
        # Invalid cases
        (b"too-short", False),
        (b"", False),
        (None, False),
        (b"not-base64-encoded@#$", False),
        (b"A" * 44, False),  # Wrong length
    ]
    
    for key, should_be_valid in test_cases:
        is_valid, error = validate_key(key)
        assert is_valid == should_be_valid
        if not should_be_valid:
            assert error is not None


def test_key_directory_creation(tmp_path):
    """Test key file creation in non-existent directory"""
    key_dir = tmp_path / "keys"
    key_file = key_dir / "test.key"
    
    # Directory shouldn't exist yet
    assert not key_dir.exists()
    
    # Generate key file
    generate_key_file(str(key_file))
    
    # Check directory was created
    assert key_dir.exists()
    assert key_file.exists()


def test_key_functionality(tmp_path):
    """Test that generated key works with Fernet"""
    key_file = tmp_path / "test.key"
    generate_key_file(str(key_file))
    
    # Read generated key
    with open(key_file, 'rb') as f:
        key = f.read()
    
    # Try to use key with Fernet
    fernet = Fernet(key)
    test_data = b"test message"
    encrypted = fernet.encrypt(test_data)
    decrypted = fernet.decrypt(encrypted)
    assert decrypted == test_data


def test_invalid_path():
    """Test handling of invalid file paths"""
    with pytest.raises(Exception):
        generate_key_file("/invalid/path/that/should/not/exist/key.txt")


def test_verify_existing_key(tmp_path):
    """Test verification of existing key file"""
    key_file = tmp_path / "test.key"
    
    # Generate valid key
    generate_key_file(str(key_file))
    
    # Verify the key
    with open(key_file, 'rb') as f:
        key = f.read()
    is_valid, error = validate_key(key)
    assert is_valid
    assert error is None
    
    # Corrupt the key file
    with open(key_file, 'wb') as f:
        f.write(b"invalid key")
    
    # Verify corrupted key
    with open(key_file, 'rb') as f:
        key = f.read()
    is_valid, error = validate_key(key)
    assert not is_valid
    assert error is not None


def test_key_file_permissions(tmp_path):
    """Test key file has secure permissions"""
    key_file = tmp_path / "test.key"
    generate_key_file(str(key_file))
    
    # Get file permissions
    mode = os.stat(key_file).st_mode
    
    # Check specific permissions
    assert mode & stat.S_IRUSR  # Owner read
    assert mode & stat.S_IWUSR  # Owner write
    assert not mode & stat.S_IXUSR  # Owner not execute
    assert not mode & stat.S_IRWXG  # No group permissions
    assert not mode & stat.S_IRWXO  # No other permissions


@pytest.mark.skipif(os.name == 'nt', reason="Permission tests don't apply to Windows")
def test_key_file_security(tmp_path):
    """Test key file security attributes"""
    key_file = tmp_path / "test.key"
    generate_key_file(str(key_file))
    
    # Check file mode (should be 0600)
    mode = os.stat(key_file).st_mode & 0o777
    assert mode == 0o600, f"Expected mode 0600, got {oct(mode)}"


def test_multiple_keys(tmp_path):
    """Test generating multiple keys"""
    # Generate multiple keys
    keys = []
    for i in range(5):
        key_file = tmp_path / f"key_{i}.key"
        generate_key_file(str(key_file))
        with open(key_file, 'rb') as f:
            keys.append(f.read())
    
    # Verify all keys are valid and unique
    assert len(set(keys)) == len(keys), "Generated keys are not unique"
    for key in keys:
        is_valid, _ = validate_key(key)
        assert is_valid


@pytest.fixture
def cleanup_key_files():
    """Fixture to clean up test key files"""
    yield
    # Clean up any test key files in current directory
    for file in os.listdir('.'):
        if file.endswith('.key'):
            try:
                os.remove(file)
            except (OSError, PermissionError):
                pass
