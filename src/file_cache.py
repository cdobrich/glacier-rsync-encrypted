from io import BytesIO

class FileCache:
    def __init__(self, f, compression=False):
        self.compression = compression
        self.f = f
        if compression:
            import zstandard as zstd
            self.cctx = zstd.ZstdCompressor()
            self.reader = self.cctx.read_to_iter(self.f, write_size=8192)
        else:
            self.reader = self.f
        self.next_chunk = b""

    def grow_chunk(self):
        new_chunk = next(self.reader)
        if new_chunk is None:
            raise StopIteration()
        self.next_chunk = self.next_chunk + new_chunk

    def read(self, n):
        if self.compression:
            if self.next_chunk is None:
                return None
        else:
            if isinstance(self.reader, BytesIO):
                if self.reader.tell() >= len(self.reader.getvalue()):
                    return None
            elif not self.reader.readable():
                return None
        try:
            if not self.compression:
                if isinstance(self.reader, BytesIO):
                    rv = self.reader.read(n)
                else:
                    rv = self.reader.read(n)
            else:
                while len(self.next_chunk) < n:
                    self.grow_chunk()
                rv = self.next_chunk[:n]
                self.next_chunk = self.next_chunk[n:]
            return rv
        except StopIteration:
            rv = self.next_chunk
            self.next_chunk = None
            return rv
