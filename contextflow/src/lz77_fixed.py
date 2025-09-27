"""
Fixed LZ77 Implementation with Proper Match Encoding
Fixes the null-byte replacement bug in the original implementation
"""

import struct
from typing import Tuple, List, Optional
import numpy as np


class FixedLZ77:
    """
    Corrected LZ77 compression with proper match encoding.

    Match format: [0xFF][dist_hi][dist_lo][length]
    Literal format: [byte] (if byte != 0xFF)
    Escaped 0xFF: [0xFF][0x00][0x00][0x01]
    """

    def __init__(self, window_size: int = 32768, min_match: int = 3, max_match: int = 258):
        """
        Initialize LZ77 compressor

        Args:
            window_size: Size of sliding window (default 32KB)
            min_match: Minimum match length to encode
            max_match: Maximum match length
        """
        self.window_size = window_size
        self.min_match = min_match
        self.max_match = max_match
        self.MATCH_MARKER = 0xFF

    def find_match(self, data: bytes, pos: int, window_start: int = None) -> Tuple[int, int]:
        """
        Find the longest match in the sliding window

        Args:
            data: Input data
            pos: Current position
            window_start: Start of window (for optimization)

        Returns:
            (distance, length) of best match, or (0, 0) if no match
        """
        if pos >= len(data):
            return 0, 0

        # Determine search window
        if window_start is None:
            window_start = max(0, pos - self.window_size)

        best_distance = 0
        best_length = 0

        # Search for matches in the window
        for search_pos in range(window_start, pos):
            # Calculate potential match length
            match_len = 0
            max_possible = min(self.max_match, len(data) - pos)

            while (match_len < max_possible and
                   data[search_pos + match_len] == data[pos + match_len]):
                match_len += 1

            # Update best match if this is better
            if match_len >= self.min_match and match_len > best_length:
                best_distance = pos - search_pos
                best_length = match_len

                # Early exit if we found maximum match
                if best_length >= self.max_match:
                    break

        return best_distance, best_length

    def encode_match(self, distance: int, length: int) -> bytes:
        """
        Encode a match reference

        Args:
            distance: Distance to match start (1-65535)
            length: Match length (3-255)

        Returns:
            4-byte encoded match
        """
        # Clamp values to valid ranges
        distance = min(max(distance, 1), 65535)
        length = min(max(length, self.min_match), 255)

        return bytes([
            self.MATCH_MARKER,
            (distance >> 8) & 0xFF,
            distance & 0xFF,
            length
        ])

    def encode_literal(self, byte: int) -> bytes:
        """
        Encode a literal byte

        Args:
            byte: Byte value (0-255)

        Returns:
            Encoded literal (1 or 4 bytes)
        """
        if byte != self.MATCH_MARKER:
            # Normal literal
            return bytes([byte])
        else:
            # Escaped 0xFF - encoded as special match with distance=0, length=1
            return bytes([self.MATCH_MARKER, 0x00, 0x00, 0x01])

    def compress(self, data: bytes) -> bytes:
        """
        Compress data using LZ77

        Args:
            data: Input data

        Returns:
            Compressed data
        """
        if not data:
            return b''

        result = bytearray()
        i = 0

        # Optional: Add uncompressed size header for easier decompression
        # result.extend(struct.pack('<I', len(data)))

        while i < len(data):
            # Find best match in sliding window
            distance, length = self.find_match(data, i)

            if length >= self.min_match:
                # Encode as match
                result.extend(self.encode_match(distance, length))
                i += length
            else:
                # Encode as literal
                result.extend(self.encode_literal(data[i]))
                i += 1

        return bytes(result)

    def decompress(self, data: bytes) -> bytes:
        """
        Decompress LZ77-compressed data

        Args:
            data: Compressed data

        Returns:
            Original data
        """
        if not data:
            return b''

        result = bytearray()
        i = 0

        while i < len(data):
            if data[i] == self.MATCH_MARKER:
                # This is either a match or escaped 0xFF
                if i + 3 >= len(data):
                    # Incomplete match - treat as corruption
                    break

                # Read match parameters
                dist_hi = data[i + 1]
                dist_lo = data[i + 2]
                length = data[i + 3]

                distance = (dist_hi << 8) | dist_lo

                if distance == 0 and length == 1:
                    # Escaped 0xFF literal
                    result.append(self.MATCH_MARKER)
                else:
                    # Normal match - copy from history
                    if distance > len(result):
                        # Invalid distance - treat as corruption
                        break

                    # Copy bytes from history
                    # Note: We need to copy byte-by-byte because the match
                    # might overlap with its own output (e.g., RLE compression)
                    for _ in range(length):
                        if distance <= len(result):
                            # Copy from the position 'distance' bytes back
                            result.append(result[-distance])
                        else:
                            # Should not happen with valid compressed data
                            break

                i += 4
            else:
                # Literal byte
                result.append(data[i])
                i += 1

        return bytes(result)

    def compress_with_stats(self, data: bytes) -> Tuple[bytes, dict]:
        """
        Compress with statistics for debugging

        Args:
            data: Input data

        Returns:
            (compressed_data, statistics)
        """
        if not data:
            return b'', {'input_size': 0, 'output_size': 0, 'ratio': 0}

        matches = 0
        literals = 0
        total_match_length = 0
        result = bytearray()
        i = 0

        while i < len(data):
            distance, length = self.find_match(data, i)

            if length >= self.min_match:
                result.extend(self.encode_match(distance, length))
                matches += 1
                total_match_length += length
                i += length
            else:
                result.extend(self.encode_literal(data[i]))
                literals += 1
                i += 1

        compressed = bytes(result)

        stats = {
            'input_size': len(data),
            'output_size': len(compressed),
            'ratio': len(data) / len(compressed) if compressed else 0,
            'matches': matches,
            'literals': literals,
            'avg_match_length': total_match_length / matches if matches else 0,
            'match_percentage': (total_match_length / len(data)) * 100 if data else 0
        }

        return compressed, stats


class FastLZ77(FixedLZ77):
    """
    Optimized LZ77 with hash table for faster matching
    """

    def __init__(self, window_size: int = 32768, min_match: int = 3, max_match: int = 258):
        super().__init__(window_size, min_match, max_match)
        self.hash_bits = 15
        self.hash_size = 1 << self.hash_bits
        self.hash_mask = self.hash_size - 1

    def hash3(self, data: bytes, pos: int) -> int:
        """Compute hash of 3 bytes at position"""
        if pos + 2 >= len(data):
            return 0
        # Simple but effective hash
        return ((data[pos] << 10) ^ (data[pos + 1] << 5) ^ data[pos + 2]) & self.hash_mask

    def compress(self, data: bytes) -> bytes:
        """
        Compress using hash table for faster matching
        """
        if not data or len(data) < self.min_match:
            return super().compress(data)  # Fall back to simple method

        # Initialize hash table
        hash_table = {}  # hash -> list of positions

        # Populate initial hash table for first window
        for i in range(min(self.window_size, len(data) - 2)):
            h = self.hash3(data, i)
            if h not in hash_table:
                hash_table[h] = []
            hash_table[h].append(i)

        result = bytearray()
        i = 0

        while i < len(data):
            if i + self.min_match > len(data):
                # Not enough data for a match
                result.extend(self.encode_literal(data[i]))
                i += 1
                continue

            # Look up in hash table
            h = self.hash3(data, i)
            best_distance = 0
            best_length = 0

            if h in hash_table:
                # Check all positions with same hash
                for pos in hash_table[h]:
                    if pos >= i:  # Skip positions ahead
                        break
                    if i - pos > self.window_size:  # Outside window
                        continue

                    # Check actual match length
                    match_len = 0
                    max_len = min(self.max_match, len(data) - i)

                    while match_len < max_len and data[pos + match_len] == data[i + match_len]:
                        match_len += 1

                    if match_len >= self.min_match and match_len > best_length:
                        best_distance = i - pos
                        best_length = match_len

                        if best_length >= self.max_match:
                            break  # Can't do better

            if best_length >= self.min_match:
                # Encode match
                result.extend(self.encode_match(best_distance, best_length))

                # Update hash table for bytes we're skipping
                for j in range(i, min(i + best_length, len(data) - 2)):
                    h = self.hash3(data, j)
                    if h not in hash_table:
                        hash_table[h] = []
                    hash_table[h].append(j)
                    # Limit entries per hash to prevent slowdown
                    if len(hash_table[h]) > 8:
                        hash_table[h] = hash_table[h][-8:]

                i += best_length
            else:
                # Encode literal
                result.extend(self.encode_literal(data[i]))

                # Update hash table
                if i < len(data) - 2:
                    h = self.hash3(data, i)
                    if h not in hash_table:
                        hash_table[h] = []
                    hash_table[h].append(i)
                    if len(hash_table[h]) > 8:
                        hash_table[h] = hash_table[h][-8:]

                i += 1

        return bytes(result)


# Test the implementation
if __name__ == "__main__":
    import time
    import zlib

    # Test basic functionality
    compressor = FixedLZ77()
    test_data = b"The quick brown fox jumps over the lazy dog. " * 100

    print(f"Original size: {len(test_data)} bytes")

    # Test our LZ77
    start = time.time()
    compressed = compressor.compress(test_data)
    compress_time = time.time() - start

    start = time.time()
    decompressed = compressor.decompress(compressed)
    decompress_time = time.time() - start

    print(f"\nFixed LZ77:")
    print(f"  Compressed size: {len(compressed)} bytes")
    print(f"  Ratio: {len(test_data) / len(compressed):.2f}x")
    print(f"  Compress time: {compress_time*1000:.2f}ms")
    print(f"  Decompress time: {decompress_time*1000:.2f}ms")
    print(f"  Integrity: {'PASS' if decompressed == test_data else 'FAIL'}")

    # Compare with zlib
    start = time.time()
    zlib_compressed = zlib.compress(test_data, 6)
    zlib_time = time.time() - start

    print(f"\nZlib comparison:")
    print(f"  Compressed size: {len(zlib_compressed)} bytes")
    print(f"  Ratio: {len(test_data) / len(zlib_compressed):.2f}x")
    print(f"  Time: {zlib_time*1000:.2f}ms")

    # Test with stats
    compressed_stats, stats = compressor.compress_with_stats(test_data)
    print(f"\nCompression statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}")

    # Test FastLZ77
    fast_compressor = FastLZ77()
    start = time.time()
    fast_compressed = fast_compressor.compress(test_data)
    fast_time = time.time() - start

    print(f"\nFast LZ77:")
    print(f"  Compressed size: {len(fast_compressed)} bytes")
    print(f"  Ratio: {len(test_data) / len(fast_compressed):.2f}x")
    print(f"  Time: {fast_time*1000:.2f}ms")
    print(f"  Speedup: {compress_time / fast_time:.2f}x")

    # Verify integrity
    fast_decompressed = fast_compressor.decompress(fast_compressed)
    print(f"  Integrity: {'PASS' if fast_decompressed == test_data else 'FAIL'}")