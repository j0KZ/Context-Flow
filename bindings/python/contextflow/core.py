"""
ContextFlow Core Python Implementation
Pure Python implementation with optional C extension
"""

import ctypes
import os
import sys
import struct
import zlib
from enum import IntEnum
from typing import Optional, List, Tuple, Union, BinaryIO
from dataclasses import dataclass
import numpy as np

try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False

from .exceptions import *

__version__ = "4.0.0"

# Try to load C library
_lib = None
_lib_path = None

def _load_c_library():
    """Load the C library if available"""
    global _lib, _lib_path

    # Try different library names based on platform
    if sys.platform == "win32":
        lib_names = ["contextflow.dll", "libcontextflow.dll"]
    elif sys.platform == "darwin":
        lib_names = ["libcontextflow.dylib", "contextflow.dylib"]
    else:
        lib_names = ["libcontextflow.so", "contextflow.so"]

    # Search paths
    search_paths = [
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "c", "build"),
        "/usr/local/lib",
        "/usr/lib",
    ]

    for path in search_paths:
        for name in lib_names:
            try:
                lib_path = os.path.join(path, name)
                if os.path.exists(lib_path):
                    _lib = ctypes.CDLL(lib_path)
                    _lib_path = lib_path
                    _setup_c_functions()
                    return True
            except:
                continue

    return False

def _setup_c_functions():
    """Setup C function signatures"""
    if not _lib:
        return

    # cf_compress
    _lib.cf_compress.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),  # input
        ctypes.c_size_t,                  # input_size
        ctypes.POINTER(ctypes.c_uint8),  # output
        ctypes.POINTER(ctypes.c_size_t), # output_size
        ctypes.c_int,                     # level
    ]
    _lib.cf_compress.restype = ctypes.c_int

    # cf_decompress
    _lib.cf_decompress.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),  # input
        ctypes.c_size_t,                  # input_size
        ctypes.POINTER(ctypes.c_uint8),  # output
        ctypes.POINTER(ctypes.c_size_t), # output_size
    ]
    _lib.cf_decompress.restype = ctypes.c_int

    # cf_compress_bound
    _lib.cf_compress_bound.argtypes = [ctypes.c_size_t]
    _lib.cf_compress_bound.restype = ctypes.c_size_t

# Try to load C library on import
HAS_C_EXTENSION = _load_c_library()


class CompressionLevel(IntEnum):
    """Compression levels"""
    FASTEST = 1
    FAST = 3
    DEFAULT = 6
    BETTER = 7
    BEST = 9


class Mode(IntEnum):
    """Compression modes"""
    STANDARD = 0
    TURBO = 1
    QUANTUM = 2
    STREAMING = 3
    DELTA = 4
    DICTIONARY = 5


@dataclass
class Statistics:
    """Compression statistics"""
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    compression_speed_mbps: float = 0.0
    decompression_speed_mbps: float = 0.0
    memory_used: int = 0
    checksum: int = 0


class Context:
    """Compression context for advanced operations"""

    def __init__(self, mode: Mode = Mode.STANDARD, level: CompressionLevel = CompressionLevel.DEFAULT):
        self.mode = mode
        self.level = level
        self.stats = Statistics()
        self.dictionary = None

        # LZ77 components
        self.window_size = 32768
        self.window = bytearray(self.window_size)
        self.window_pos = 0
        self.hash_table = {}

        # Context modeling
        self.contexts = [{} for _ in range(4)]
        self.history = bytearray(256)

    def compress(self, data: bytes) -> bytes:
        """Compress data using this context"""
        if not data:
            return b''

        # Use C library if available
        if HAS_C_EXTENSION and _lib:
            return self._compress_c(data)

        # Pure Python implementation
        return self._compress_python(data)

    def decompress(self, data: bytes) -> bytes:
        """Decompress data using this context"""
        if not data:
            return b''

        # Use C library if available
        if HAS_C_EXTENSION and _lib:
            return self._decompress_c(data)

        # Pure Python implementation
        return self._decompress_python(data)

    def _compress_c(self, data: bytes) -> bytes:
        """Compress using C library"""
        input_array = (ctypes.c_uint8 * len(data))(*data)
        output_size = _lib.cf_compress_bound(len(data))
        output_array = (ctypes.c_uint8 * output_size)()
        output_size_ref = ctypes.c_size_t(output_size)

        result = _lib.cf_compress(
            input_array,
            len(data),
            output_array,
            ctypes.byref(output_size_ref),
            self.level
        )

        if result != 0:
            raise CompressionError(f"C compression failed with error {result}")

        return bytes(output_array[:output_size_ref.value])

    def _decompress_c(self, data: bytes) -> bytes:
        """Decompress using C library"""
        input_array = (ctypes.c_uint8 * len(data))(*data)
        output_size = len(data) * 10  # Estimate
        output_array = (ctypes.c_uint8 * output_size)()
        output_size_ref = ctypes.c_size_t(output_size)

        result = _lib.cf_decompress(
            input_array,
            len(data),
            output_array,
            ctypes.byref(output_size_ref)
        )

        if result != 0:
            raise DecompressionError(f"C decompression failed with error {result}")

        return bytes(output_array[:output_size_ref.value])

    def _compress_python(self, data: bytes) -> bytes:
        """Pure Python compression implementation"""
        import time
        start_time = time.time()

        # Simple LZ77-like compression
        output = bytearray()

        # Header
        output.extend(b'CTXF')
        output.append(self.mode)
        output.append(self.level)
        output.extend(struct.pack('>I', len(data)))

        # Process data
        pos = 0
        while pos < len(data):
            # Find match in window
            best_match = self._find_match(data, pos)

            if best_match and best_match[1] >= 3:
                # Encode match
                distance, length = best_match
                output.append(0x80 | min(length, 127))
                output.extend(struct.pack('>H', distance))
                pos += length
            else:
                # Encode literal
                output.append(data[pos])
                pos += 1

            # Update window
            if pos < len(data):
                self._update_window(data[pos])

        # Add checksum
        checksum = zlib.crc32(data)
        output.extend(struct.pack('>I', checksum))

        # Update statistics
        elapsed = time.time() - start_time
        self.stats.original_size = len(data)
        self.stats.compressed_size = len(output)
        self.stats.compression_ratio = len(data) / len(output) if output else 0
        self.stats.compression_speed_mbps = (len(data) / 1024 / 1024) / elapsed if elapsed > 0 else 0
        self.stats.checksum = checksum

        return bytes(output)

    def _decompress_python(self, data: bytes) -> bytes:
        """Pure Python decompression implementation"""
        if len(data) < 14:
            raise InvalidFormatError("Data too short")

        # Check header
        if data[:4] != b'CTXF':
            raise InvalidFormatError("Invalid header")

        mode = data[4]
        level = data[5]
        original_size = struct.unpack('>I', data[6:10])[0]

        output = bytearray()
        pos = 10

        # Decompress
        while pos < len(data) - 4:  # Keep 4 bytes for checksum
            if pos >= len(data):
                break

            byte = data[pos]
            pos += 1

            if byte & 0x80:
                # Match
                length = byte & 0x7F
                if pos + 2 > len(data):
                    break
                distance = struct.unpack('>H', data[pos:pos+2])[0]
                pos += 2

                # Copy from output buffer
                for _ in range(length):
                    if len(output) >= distance:
                        output.append(output[-distance])
            else:
                # Literal
                output.append(byte)

            if len(output) >= original_size:
                break

        # Verify checksum
        stored_checksum = struct.unpack('>I', data[-4:])[0]
        calculated_checksum = zlib.crc32(output)

        if stored_checksum != calculated_checksum:
            raise ChecksumMismatchError("Checksum verification failed")

        return bytes(output)

    def _find_match(self, data: bytes, pos: int) -> Optional[Tuple[int, int]]:
        """Find best match in window"""
        if pos < 3 or pos >= len(data) - 2:
            return None

        # Simple hash-based matching
        pattern = data[pos:pos+3]
        best_distance = 0
        best_length = 0

        # Search in window
        window_start = max(0, pos - self.window_size)
        for i in range(window_start, pos):
            if data[i:i+3] == pattern:
                # Extend match
                length = 3
                while (i + length < pos and
                       pos + length < len(data) and
                       data[i + length] == data[pos + length] and
                       length < 258):
                    length += 1

                if length > best_length:
                    best_length = length
                    best_distance = pos - i

        if best_length >= 3:
            return (best_distance, best_length)
        return None

    def _update_window(self, byte: int):
        """Update sliding window"""
        self.window[self.window_pos] = byte
        self.window_pos = (self.window_pos + 1) % self.window_size

    def reset(self):
        """Reset context for reuse"""
        self.stats = Statistics()
        self.window = bytearray(self.window_size)
        self.window_pos = 0
        self.hash_table.clear()
        self.contexts = [{} for _ in range(4)]
        self.history = bytearray(256)

    def load_dictionary(self, dictionary: bytes):
        """Load compression dictionary"""
        self.dictionary = dictionary

    def get_statistics(self) -> Statistics:
        """Get compression statistics"""
        return self.stats


class StreamCompressor:
    """Streaming compression for large files"""

    def __init__(self, level: CompressionLevel = CompressionLevel.DEFAULT, chunk_size: int = 65536):
        self.context = Context(Mode.STREAMING, level)
        self.chunk_size = chunk_size
        self.buffer = bytearray()

    def compress_chunk(self, chunk: bytes, is_last: bool = False) -> bytes:
        """Compress a chunk of data"""
        self.buffer.extend(chunk)
        output = bytearray()

        # Process full chunks
        while len(self.buffer) >= self.chunk_size:
            block = bytes(self.buffer[:self.chunk_size])
            self.buffer = self.buffer[self.chunk_size:]
            compressed = self.context.compress(block)
            output.extend(compressed)

        # Process remaining on last chunk
        if is_last and self.buffer:
            compressed = self.context.compress(bytes(self.buffer))
            output.extend(compressed)
            self.buffer.clear()

        return bytes(output)

    def compress_stream(self, input_stream: BinaryIO, output_stream: BinaryIO):
        """Compress from input stream to output stream"""
        while True:
            chunk = input_stream.read(self.chunk_size)
            if not chunk:
                # Process any remaining data
                if self.buffer:
                    compressed = self.compress_chunk(b'', is_last=True)
                    output_stream.write(compressed)
                break

            compressed = self.compress_chunk(chunk, is_last=False)
            if compressed:
                output_stream.write(compressed)


class DictionaryBuilder:
    """Build compression dictionaries from samples"""

    def __init__(self):
        self.samples = []

    def add_sample(self, sample: bytes):
        """Add a sample for dictionary training"""
        self.samples.append(sample)

    def build(self, max_size: int = 32768) -> bytes:
        """Build dictionary from samples"""
        if not self.samples:
            raise InvalidInputError("No samples provided")

        # Frequency analysis
        pattern_freq = {}

        for sample in self.samples:
            for i in range(len(sample) - 3):
                pattern = sample[i:i+4]
                pattern_freq[pattern] = pattern_freq.get(pattern, 0) + 1

        # Sort by frequency
        sorted_patterns = sorted(pattern_freq.items(), key=lambda x: x[1], reverse=True)

        # Build dictionary
        dictionary = bytearray()
        for pattern, _ in sorted_patterns:
            if len(dictionary) + len(pattern) > max_size:
                break
            dictionary.extend(pattern)

        return bytes(dictionary)

    def clear(self):
        """Clear all samples"""
        self.samples.clear()


class Delta:
    """Delta compression for version control"""

    @staticmethod
    def compute(base: bytes, target: bytes) -> bytes:
        """Compute delta between base and target"""
        output = bytearray()

        # Header
        output.extend(b'DLTA')
        output.extend(struct.pack('>I', len(base)))
        output.extend(struct.pack('>I', len(target)))

        # Find common prefix
        common_prefix = 0
        while (common_prefix < len(base) and
               common_prefix < len(target) and
               base[common_prefix] == target[common_prefix]):
            common_prefix += 1

        if common_prefix > 0:
            # COPY operation
            output.append(0x01)
            output.extend(struct.pack('>I', common_prefix))

        # ADD remaining target
        if common_prefix < len(target):
            output.append(0x02)
            output.extend(struct.pack('>I', len(target) - common_prefix))
            output.extend(target[common_prefix:])

        return bytes(output)

    @staticmethod
    def apply(base: bytes, delta: bytes) -> bytes:
        """Apply delta to base to get target"""
        if len(delta) < 12:
            raise InvalidFormatError("Delta too short")

        if delta[:4] != b'DLTA':
            raise InvalidFormatError("Invalid delta header")

        base_size = struct.unpack('>I', delta[4:8])[0]
        target_size = struct.unpack('>I', delta[8:12])[0]

        output = bytearray()
        pos = 12

        while pos < len(delta):
            op = delta[pos]
            pos += 1

            if op == 0x01:  # COPY
                length = struct.unpack('>I', delta[pos:pos+4])[0]
                pos += 4
                output.extend(base[:length])

            elif op == 0x02:  # ADD
                length = struct.unpack('>I', delta[pos:pos+4])[0]
                pos += 4
                output.extend(delta[pos:pos+length])
                pos += length

            else:
                raise InvalidFormatError(f"Unknown delta operation: {op}")

        return bytes(output)


# Simple API functions
def compress(data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
    """Simple compression function"""
    ctx = Context(Mode.STANDARD, level)
    return ctx.compress(data)


def decompress(data: bytes) -> bytes:
    """Simple decompression function"""
    ctx = Context()
    return ctx.decompress(data)


def version() -> str:
    """Get library version"""
    return __version__