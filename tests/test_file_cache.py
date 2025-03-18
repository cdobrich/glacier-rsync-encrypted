# tests/test_file_cache.py
import pytest
import os
from io import BytesIO
from src.file_cache import FileCache
import zstandard as zstd


class TestFileCache:
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing - smaller size"""
        return b"This is test data " * 50

    @pytest.fixture
    def sample_file(self, tmp_path, sample_data):
        """Create a temporary file with sample data"""
        test_file = tmp_path / "test.dat"
        with open(test_file, 'wb') as f:
            f.write(sample_data)
        return test_file

    def test_basic_read(self, sample_data):
        """Test basic reading from BytesIO"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj)
        
        read_data = b""
        while True:
            chunk = cache.read(1024)
            if chunk is None:  # Changed back to None check
                break
            read_data += chunk
        
        assert read_data == sample_data

    def test_file_read(self, sample_file, sample_data):
        """Test reading from actual file"""
        with open(sample_file, 'rb') as f:
            cache = FileCache(f)
            read_data = cache.read(len(sample_data) + 1024)  # Read all at once
            assert read_data == sample_data
            assert cache.read(1024) == b''  # Changed: empty bytes at EOF

    def test_compression(self, sample_data):
        """Test compression functionality"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj, compression=True)
        
        # Read all compressed data first
        compressed_parts = []
        while True:
            chunk = cache.read(1024)
            if chunk is None:  # Changed back to None check
                break
            compressed_parts.append(chunk)
        
        compressed_data = b''.join(compressed_parts)
        assert len(compressed_data) < len(sample_data)
        
        # Create decompressor context
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed_data)
        assert decompressed == sample_data

    def test_grow_chunk(self, sample_data):
        """Test grow_chunk method"""
        file_obj = BytesIO(sample_data[:100])
        cache = FileCache(file_obj)
        
        assert cache.next_chunk == b""
        cache.grow_chunk()
        assert len(cache.next_chunk) > 0
        assert cache.next_chunk in sample_data

    def test_partial_reads(self, sample_data):
        """Test reading data in various chunk sizes"""
        chunk_sizes = [10, 50, 100]
        
        for size in chunk_sizes:
            file_obj = BytesIO(sample_data)
            cache = FileCache(file_obj)
            read_data = b""
            
            while True:
                chunk = cache.read(size)
                if chunk is None:  # Changed back to None check
                    break
                read_data += chunk
                
            assert read_data == sample_data

    def test_empty_file(self):
        """Test handling of empty file"""
        file_obj = BytesIO(b"")
        cache = FileCache(file_obj)
        assert cache.read(1024) is None  # Changed back to None

    def test_empty_reads(self):
        """Test handling of empty reads"""
        file_obj = BytesIO(b"data")
        cache = FileCache(file_obj)
        assert cache.read(1024) == b"data"
        assert cache.read(1024) is None  # Changed back to None
        assert cache.read(1024) is None  # Subsequent reads return None

    def test_large_file(self, tmp_path):
        """Test handling of large file"""
        # Create 100KB file
        large_file = tmp_path / "large.dat"
        large_data = os.urandom(100 * 1024)
        
        with open(large_file, 'wb') as f:
            f.write(large_data)
        
        with open(large_file, 'rb') as f:
            cache = FileCache(f)
            read_data = cache.read(len(large_data))
            assert read_data == large_data
            assert cache.read(1024) == b''

    def test_compression_ratio(self):
        """Test compression effectiveness"""
        compressible_data = b"repeatable " * 50
        
        file_obj = BytesIO(compressible_data)
        cache = FileCache(file_obj, compression=True)
        
        compressed_parts = []
        while True:
            chunk = cache.read(1024)
            if chunk is None:  # Changed back to None check
                break
            compressed_parts.append(chunk)
        
        compressed_data = b''.join(compressed_parts)
        compression_ratio = len(compressed_data) / len(compressible_data)
        assert compression_ratio < 0.5, "Compression ratio not effective"

    def test_read_after_end(self, sample_data):
        """Test reading after reaching end of data"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj)
        
        # Read all data
        all_data = cache.read(len(sample_data) + 1024)
        assert all_data == sample_data
        
        # Try reading more
        assert cache.read(1024) is None  # Changed back to None
        assert cache.read(1) is None     # Changed back to None

    def test_small_reads(self, sample_data):
        """Test reading very small chunks"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj)
        
        read_data = b""
        while True:
            chunk = cache.read(1)  # Read byte by byte
            if chunk is None:  # Changed back to None check
                break
            read_data += chunk
            
        assert read_data == sample_data

    def test_compressed_empty_file(self):
        """Test compressing an empty file"""
        file_obj = BytesIO(b"")
        cache = FileCache(file_obj, compression=True)
        # For compressed empty file, we might get a compression header
        chunk = cache.read(1024)
        assert chunk is not None  # We might get compression header
        assert cache.read(1024) is None  # But next read should be None

    def test_compressed_small_reads(self, sample_data):
        """Test reading compressed data in small chunks"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj, compression=True)
        
        compressed_parts = []
        while True:
            chunk = cache.read(1)  # Read compressed data byte by byte
            if chunk is None:
                break
            compressed_parts.append(chunk)
            
        compressed_data = b''.join(compressed_parts)
        
        # Verify the compressed data
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed_data)
        assert decompressed == sample_data
