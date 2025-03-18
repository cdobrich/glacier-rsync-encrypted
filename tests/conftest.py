# tests/conftest.py
import pytest
import tempfile
import os

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

@pytest.fixture
def sample_files(temp_dir):
    files = []
    sizes = [1024, 1024*1024, 2*1024*1024]  # 1KB, 1MB, 2MB
    for i, size in enumerate(sizes):
        path = os.path.join(temp_dir, f'test_file_{i}.dat')
        with open(path, 'wb') as f:
            f.write(os.urandom(size))
        files.append(path)
    return files

@pytest.fixture
def mock_args(temp_dir):
    class Args:
        def __init__(self):
            self.log_level = "INFO"
            self.db = "test.db"
            self.vault = "test-vault"
            self.region = "us-east-1"
            self.compress = False
            self.part_size = 1048576
            self.desc = "test description"
            self.encrypt = False
            self.encryption_key = None
            self.src = temp_dir  # Use the temporary directory
    return Args()

@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up test database before and after each test"""
    if os.path.exists("test.db"):
        os.remove("test.db")
    yield
    if os.path.exists("test.db"):
        os.remove("test.db")
