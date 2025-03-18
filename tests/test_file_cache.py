# tests/test_file_cache.py
import pytest
from src.file_cache import FileCache
import os

def test_basic_read(sample_files):
    test_file = sample_files[0]
    with open(test_file, 'rb') as f:
        original_content = f.read()
    
    with open(test_file, 'rb') as f:
        cache = FileCache(f)
        cached_content = cache.read(len(original_content))
        assert cached_content == original_content

# ... more tests
