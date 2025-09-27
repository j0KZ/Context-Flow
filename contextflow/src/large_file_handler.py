"""
Large File Handler with Memory-Mapped Files
Enables compression of files >100KB without timeout
"""

import mmap
import struct
import os
from typing import Optional, Callable, Tuple
from pathlib import Path
import tempfile

class LargeFileHandler:
    """
    Handles large file compression using memory-mapped files
    Processes files in streaming chunks to avoid memory overflow
    """

    def __init__(self, chunk_size: int = 65536):
        """
        Initialize large file handler

        Args:
            chunk_size: Size of chunks to process (default 64KB)
        """
        self.chunk_size = chunk_size
        self.header_size = 16  # Header for storing metadata

    def compress_file(self, input_path: str, output_path: str,
                      compressor: Callable[[bytes], bytes]) -> bool:
        """
        Compress a large file using memory-mapped I/O

        Args:
            input_path: Path to input file
            output_path: Path to output file
            compressor: Function that compresses bytes

        Returns:
            True if successful, False otherwise
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            if not input_path.exists():
                return False

            file_size = input_path.stat().st_size

            # Handle empty files
            if file_size == 0:
                output_path.write_bytes(self._create_header(0, 0))
                return True

            # Use memory mapping for large files
            if file_size > self.chunk_size:
                return self._compress_large_file(input_path, output_path, compressor)
            else:
                # Small file - process normally
                data = input_path.read_bytes()
                compressed = compressor(data)

                # Write with header
                header = self._create_header(file_size, len(compressed))
                output_path.write_bytes(header + compressed)
                return True

        except Exception as e:
            print(f"Error compressing file: {e}")
            return False

    def _compress_large_file(self, input_path: Path, output_path: Path,
                            compressor: Callable[[bytes], bytes]) -> bool:
        """
        Compress a large file in chunks using memory mapping

        Args:
            input_path: Input file path
            output_path: Output file path
            compressor: Compression function

        Returns:
            True if successful
        """
        try:
            file_size = input_path.stat().st_size

            # Open input file with memory mapping
            with open(input_path, 'rb') as input_file:
                # Create output file
                with open(output_path, 'wb') as output_file:
                    # Write placeholder header
                    output_file.write(b'\x00' * self.header_size)

                    # Memory map the input file
                    if file_size > 0:
                        with mmap.mmap(input_file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped:
                            compressed_size = 0
                            chunk_count = 0

                            # Process in chunks
                            for i in range(0, file_size, self.chunk_size):
                                # Read chunk
                                chunk_end = min(i + self.chunk_size, file_size)
                                chunk = mmapped[i:chunk_end]

                                # Compress chunk
                                compressed_chunk = compressor(chunk)

                                # Write chunk header and data
                                chunk_header = struct.pack('<II',
                                                         len(chunk),  # Original size
                                                         len(compressed_chunk))  # Compressed size
                                output_file.write(chunk_header)
                                output_file.write(compressed_chunk)

                                compressed_size += len(chunk_header) + len(compressed_chunk)
                                chunk_count += 1

                                # Progress indicator for very large files
                                if chunk_count % 100 == 0:
                                    progress = (i / file_size) * 100
                                    print(f"  Progress: {progress:.1f}%", end='\r')

                    # Update header with final information
                    output_file.seek(0)
                    header = self._create_header(file_size, compressed_size, chunked=True)
                    output_file.write(header)

            print(f"  Compressed {file_size} bytes to {output_path.stat().st_size} bytes")
            return True

        except Exception as e:
            print(f"Error in large file compression: {e}")
            return False

    def decompress_file(self, input_path: str, output_path: str,
                       decompressor: Callable[[bytes], bytes]) -> bool:
        """
        Decompress a file

        Args:
            input_path: Path to compressed file
            output_path: Path to output file
            decompressor: Function that decompresses bytes

        Returns:
            True if successful
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            if not input_path.exists():
                return False

            # Read header
            with open(input_path, 'rb') as f:
                header = f.read(self.header_size)

                if len(header) < self.header_size:
                    return False

                orig_size, comp_size, flags = self._parse_header(header)

                if flags & 0x01:  # Chunked
                    return self._decompress_chunked(input_path, output_path, decompressor)
                else:
                    # Simple decompression
                    compressed = f.read(comp_size)
                    decompressed = decompressor(compressed)
                    output_path.write_bytes(decompressed)
                    return True

        except Exception as e:
            print(f"Error decompressing file: {e}")
            return False

    def _decompress_chunked(self, input_path: Path, output_path: Path,
                           decompressor: Callable[[bytes], bytes]) -> bool:
        """
        Decompress a chunked file

        Args:
            input_path: Input file path
            output_path: Output file path
            decompressor: Decompression function

        Returns:
            True if successful
        """
        try:
            with open(input_path, 'rb') as input_file:
                # Skip header
                input_file.seek(self.header_size)

                with open(output_path, 'wb') as output_file:
                    while True:
                        # Read chunk header
                        chunk_header = input_file.read(8)
                        if len(chunk_header) < 8:
                            break

                        orig_chunk_size, comp_chunk_size = struct.unpack('<II', chunk_header)

                        # Read compressed chunk
                        compressed_chunk = input_file.read(comp_chunk_size)
                        if len(compressed_chunk) < comp_chunk_size:
                            break

                        # Decompress and write
                        decompressed_chunk = decompressor(compressed_chunk)
                        output_file.write(decompressed_chunk)

            return True

        except Exception as e:
            print(f"Error in chunked decompression: {e}")
            return False

    def _create_header(self, original_size: int, compressed_size: int,
                      chunked: bool = False) -> bytes:
        """
        Create file header

        Format:
        - 4 bytes: Magic number (0x43544658 = 'CTFX')
        - 4 bytes: Original size
        - 4 bytes: Compressed size
        - 4 bytes: Flags (bit 0 = chunked)

        Args:
            original_size: Original file size
            compressed_size: Compressed data size
            chunked: Whether file is chunked

        Returns:
            16-byte header
        """
        magic = 0x43544658  # 'CTFX'
        flags = 0x01 if chunked else 0x00

        return struct.pack('<IIII', magic, original_size, compressed_size, flags)

    def _parse_header(self, header: bytes) -> Tuple[int, int, int]:
        """
        Parse file header

        Args:
            header: 16-byte header

        Returns:
            (original_size, compressed_size, flags)
        """
        magic, orig_size, comp_size, flags = struct.unpack('<IIII', header)

        if magic != 0x43544658:
            raise ValueError("Invalid file format")

        return orig_size, comp_size, flags


class StreamingCompressor:
    """
    Streaming compression for unlimited file sizes
    Processes data in small chunks with constant memory usage
    """

    def __init__(self, chunk_size: int = 32768):
        """
        Initialize streaming compressor

        Args:
            chunk_size: Size of chunks (default 32KB)
        """
        self.chunk_size = chunk_size

    def compress_stream(self, input_stream, output_stream,
                       compressor: Callable[[bytes], bytes]):
        """
        Compress data from input stream to output stream

        Args:
            input_stream: Input file-like object
            output_stream: Output file-like object
            compressor: Compression function
        """
        # Write format marker
        output_stream.write(b'STRM')

        while True:
            # Read chunk
            chunk = input_stream.read(self.chunk_size)
            if not chunk:
                break

            # Compress chunk
            compressed = compressor(chunk)

            # Write chunk size and data
            output_stream.write(struct.pack('<I', len(compressed)))
            output_stream.write(compressed)

        # Write end marker
        output_stream.write(struct.pack('<I', 0))

    def decompress_stream(self, input_stream, output_stream,
                         decompressor: Callable[[bytes], bytes]):
        """
        Decompress data from input stream to output stream

        Args:
            input_stream: Input file-like object
            output_stream: Output file-like object
            decompressor: Decompression function
        """
        # Check format marker
        marker = input_stream.read(4)
        if marker != b'STRM':
            raise ValueError("Invalid stream format")

        while True:
            # Read chunk size
            size_data = input_stream.read(4)
            if len(size_data) < 4:
                break

            chunk_size = struct.unpack('<I', size_data)[0]
            if chunk_size == 0:
                break  # End marker

            # Read and decompress chunk
            compressed = input_stream.read(chunk_size)
            decompressed = decompressor(compressed)
            output_stream.write(decompressed)


# Test implementation
if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    # Simple test compressor (just stores with marker)
    def test_compressor(data: bytes) -> bytes:
        return b'COMP' + data

    def test_decompressor(data: bytes) -> bytes:
        if data.startswith(b'COMP'):
            return data[4:]
        return data

    # Test large file handler
    handler = LargeFileHandler()

    # Create test file
    test_dir = tempfile.mkdtemp()
    test_file = Path(test_dir) / "test.dat"
    compressed_file = Path(test_dir) / "test.compressed"
    decompressed_file = Path(test_dir) / "test.decompressed"

    # Test 1: Small file
    print("Test 1: Small file")
    test_data = b"Hello, World!" * 100
    test_file.write_bytes(test_data)

    success = handler.compress_file(str(test_file), str(compressed_file), test_compressor)
    print(f"  Compression: {'Success' if success else 'Failed'}")

    success = handler.decompress_file(str(compressed_file), str(decompressed_file), test_decompressor)
    print(f"  Decompression: {'Success' if success else 'Failed'}")

    if decompressed_file.exists():
        result = decompressed_file.read_bytes()
        print(f"  Integrity: {'Pass' if result == test_data else 'Fail'}")

    # Test 2: Large file (simulated)
    print("\nTest 2: Large file (200KB)")
    large_data = b"ABCD" * 50000  # 200KB
    test_file.write_bytes(large_data)

    success = handler.compress_file(str(test_file), str(compressed_file), test_compressor)
    print(f"  Compression: {'Success' if success else 'Failed'}")

    success = handler.decompress_file(str(compressed_file), str(decompressed_file), test_decompressor)
    print(f"  Decompression: {'Success' if success else 'Failed'}")

    if decompressed_file.exists():
        result = decompressed_file.read_bytes()
        print(f"  Integrity: {'Pass' if result == large_data else 'Fail'}")
        print(f"  Original size: {len(large_data)}")
        print(f"  Decompressed size: {len(result)}")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)

    print("\nTest 3: Streaming compression")
    from io import BytesIO

    streamer = StreamingCompressor()
    test_data = b"Stream test data " * 1000

    input_stream = BytesIO(test_data)
    compressed_stream = BytesIO()

    streamer.compress_stream(input_stream, compressed_stream, test_compressor)

    compressed_stream.seek(0)
    output_stream = BytesIO()

    streamer.decompress_stream(compressed_stream, output_stream, test_decompressor)

    result = output_stream.getvalue()
    print(f"  Integrity: {'Pass' if result == test_data else 'Fail'}")
    print(f"  Original size: {len(test_data)}")
    print(f"  Result size: {len(result)}")