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

    def _read_all_chunks(self, cache):
        """Helper method to read all chunks from cache"""
        chunks = []
        while True:
            chunk = cache.read(1024)
            if chunk is None:
                break
            chunks.append(chunk)
        return b"".join(chunks)

    def test_basic_read(self, sample_data):
        """Test basic reading from BytesIO"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj)
        
        read_data = self._read_all_chunks(cache)
        assert read_data == sample_data

    def test_file_read(self, sample_file, sample_data):
        """Test reading from actual file"""
        with open(sample_file, 'rb') as f:
            cache = FileCache(f)
            read_data = cache.read(len(sample_data) + 1024)
            assert read_data == sample_data
            assert cache.read(1024) == b''  # EOF returns empty bytes

    def test_compression(self, sample_data):
        """Test compression functionality"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj, compression=True)
        
        compressed_data = self._read_all_chunks(cache)
        
        # Create decompressor context with streaming
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(BytesIO(compressed_data)) as reader:
            decompressed_data = reader.read()
            assert decompressed_data == sample_data

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
            chunks = []
            while True:
                chunk = cache.read(size)
                if chunk is None:
                    break
                chunks.append(chunk)
            
            read_data = b"".join(chunks)
            assert read_data == sample_data

    def test_empty_file(self):
        """Test handling of empty file"""
        file_obj = BytesIO(b"")
        cache = FileCache(file_obj)
        assert cache.read(1024) is None

    def test_none_handling(self):
        """Test handling of None returns"""
        file_obj = BytesIO(b"data")
        cache = FileCache(file_obj)
        assert cache.read(1024) == b"data"
        assert cache.read(1024) is None
        assert cache.read(1024) is None  # Multiple reads should still return None

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
            assert cache.read(1024) == b''  # EOF returns empty bytes

    def test_compression_ratio(self):
        """Test compression effectiveness"""
        compressible_data = b"repeatable " * 50
        
        file_obj = BytesIO(compressible_data)
        cache = FileCache(file_obj, compression=True)
        
        compressed_data = self._read_all_chunks(cache)
        compression_ratio = len(compressed_data) / len(compressible_data)
        assert compression_ratio < 0.5, "Compression ratio not effective"

    def test_read_after_end(self, sample_data):
        """Test reading after reaching end of data"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj)
        
        # Read all data
        all_data = cache.read(len(sample_data) + 1024)
        assert all_data == sample_data
        
        # Try reading more - should return None at EOF
        assert cache.read(1024) is None
        assert cache.read(1) is None  # Multiple reads should still return None

    def test_small_reads(self, sample_data):
        """Test reading very small chunks"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj)
        
        chunks = []
        while True:
            chunk = cache.read(1)  # Read byte by byte
            if chunk is None:
                break
            chunks.append(chunk)
        
        read_data = b"".join(chunks)
        assert read_data == sample_data

    def test_compression_streaming(self, sample_data):
        """Test compression with streaming decompression"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj, compression=True)
        
        compressed_data = self._read_all_chunks(cache)
        
        # Decompress using streaming
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(BytesIO(compressed_data)) as reader:
            decompressed_data = reader.read()
            assert decompressed_data == sample_data

    def test_compression_partial_reads(self, sample_data):
        """Test compression with partial reads during decompression"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj, compression=True)
        
        compressed_data = self._read_all_chunks(cache)
        
        # Decompress using streaming with small reads
        dctx = zstd.ZstdDecompressor()
        decompressed_chunks = []
        with dctx.stream_reader(BytesIO(compressed_data)) as reader:
            while True:
                chunk = reader.read(10)  # Small reads
                if not chunk:
                    break
                decompressed_chunks.append(chunk)
        
        decompressed_data = b"".join(decompressed_chunks)
        assert decompressed_data == sample_data

    def test_compression_empty(self):
        """Test compression of empty data"""
        file_obj = BytesIO(b"")
        cache = FileCache(file_obj, compression=True)
        
        compressed_data = self._read_all_chunks(cache)
        
        # Even empty data should decompress properly
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(BytesIO(compressed_data)) as reader:
            decompressed_data = reader.read()
            assert decompressed_data == b""

    def test_compression_one_byte(self):
        """Test compression of single byte"""
        file_obj = BytesIO(b"X")
        cache = FileCache(file_obj, compression=True)
        
        compressed_data = self._read_all_chunks(cache)
        
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(BytesIO(compressed_data)) as reader:
            decompressed_data = reader.read()
            assert decompressed_data == b"X"

    def test_compressed_small_reads(self, sample_data):
        """Test reading compressed data in small chunks"""
        file_obj = BytesIO(sample_data)
        cache = FileCache(file_obj, compression=True)
        
        # Read compressed data byte by byte
        chunks = []
        while True:
            chunk = cache.read(1)
            if chunk is None:
                break
            chunks.append(chunk)
        
        compressed_data = b"".join(chunks)
        
        # Use streaming decompression
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(BytesIO(compressed_data)) as reader:
            decompressed_data = reader.read()
            assert decompressed_data == sample_data
