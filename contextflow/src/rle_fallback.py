"""
Simple Run-Length Encoding fallback
100% reliable compression for ANS replacement
"""

import struct
from typing import Tuple

class RLECompressor:
    """
    Run-Length Encoding compressor
    Simple, reliable fallback when ANS fails
    """

    def __init__(self):
        self.max_run = 255  # Maximum run length in a single encoding

    def encode(self, data: bytes) -> bytes:
        """
        Encode using Run-Length Encoding

        Format: [marker][length][data]
        Marker 0x00 = RLE compressed
        Marker 0xFF = Store as-is (incompressible)

        Args:
            data: Input data

        Returns:
            RLE encoded data with header
        """
        if not data:
            return b''

        # Try RLE compression
        compressed = bytearray()
        i = 0

        while i < len(data):
            # Count run length
            run_byte = data[i]
            run_length = 1

            while i + run_length < len(data) and data[i + run_length] == run_byte:
                run_length += 1
                if run_length >= self.max_run:
                    break

            # Encode the run
            if run_length >= 3:
                # Worth compressing: [0xFF][byte][count]
                compressed.append(0xFF)
                compressed.append(run_byte)
                compressed.append(min(run_length, 255))
                i += run_length
            else:
                # Not worth compressing, store literally
                # Count literals
                lit_start = i
                i += 1
                while i < len(data):
                    # Check if next is a run
                    if i + 2 < len(data) and data[i] == data[i+1] == data[i+2]:
                        break
                    i += 1

                # Store literals: [count][bytes...]
                lit_length = i - lit_start
                while lit_length > 0:
                    chunk_size = min(lit_length, 254)  # Reserve 0xFF for runs
                    compressed.append(chunk_size)
                    compressed.extend(data[lit_start:lit_start + chunk_size])
                    lit_start += chunk_size
                    lit_length -= chunk_size

        # Check if compression is worth it
        if len(compressed) < len(data):
            # Add header: [0x00=RLE][original_length][compressed_data]
            header = b'\x00' + struct.pack('<I', len(data))
            return header + bytes(compressed)
        else:
            # Store as-is: [0xFF=uncompressed][length][data]
            header = b'\xFF' + struct.pack('<I', len(data))
            return header + data

    def decode(self, encoded: bytes) -> bytes:
        """
        Decode RLE encoded data

        Args:
            encoded: RLE encoded data with header

        Returns:
            Original data
        """
        if not encoded or len(encoded) < 5:
            return b''

        # Read header
        marker = encoded[0]
        orig_length = struct.unpack('<I', encoded[1:5])[0]

        if marker == 0xFF:
            # Stored as-is
            return encoded[5:5 + orig_length]

        if marker != 0x00:
            # Unknown format
            return b''

        # Decode RLE
        compressed = encoded[5:]
        result = bytearray()
        i = 0

        while i < len(compressed) and len(result) < orig_length:
            if i >= len(compressed):
                break

            first_byte = compressed[i]

            if first_byte == 0xFF:
                # Run encoding: [0xFF][byte][count]
                if i + 2 >= len(compressed):
                    break
                run_byte = compressed[i + 1]
                run_count = compressed[i + 2]
                result.extend([run_byte] * run_count)
                i += 3
            elif first_byte > 0:
                # Literal encoding: [count][bytes...]
                lit_count = first_byte
                if i + lit_count >= len(compressed):
                    # Read what we can
                    result.extend(compressed[i + 1:])
                    break
                else:
                    result.extend(compressed[i + 1:i + 1 + lit_count])
                    i += 1 + lit_count
            else:
                # Invalid encoding
                i += 1

        return bytes(result[:orig_length])


class SimpleFallback:
    """
    Ultra-simple fallback that always works
    Uses RLE for repetitive data, stores as-is otherwise
    """

    def __init__(self):
        self.rle = RLECompressor()

    def encode(self, data: bytes) -> bytes:
        """
        Encode data with simple fallback

        Args:
            data: Input data

        Returns:
            Encoded data
        """
        if not data:
            return b''

        # Try RLE
        return self.rle.encode(data)

    def decode(self, encoded: bytes) -> bytes:
        """
        Decode data

        Args:
            encoded: Encoded data

        Returns:
            Original data
        """
        if not encoded:
            return b''

        return self.rle.decode(encoded)


# Test implementation
if __name__ == "__main__":
    compressor = SimpleFallback()

    # Test 1: Simple text
    test1 = b"Hello, World! This is a test."
    print(f"Test 1: {test1[:30]}")
    print(f"Original length: {len(test1)}")

    encoded1 = compressor.encode(test1)
    print(f"Encoded length: {len(encoded1)}")

    decoded1 = compressor.decode(encoded1)
    print(f"Decoded: {decoded1[:30]}")
    print(f"Match: {decoded1 == test1}")

    # Test 2: Repetitive data (should compress well)
    test2 = b"AAAAAABBBBBBCCCCCC" * 10
    print(f"\nTest 2 (repetitive) length: {len(test2)}")

    encoded2 = compressor.encode(test2)
    print(f"Encoded length: {len(encoded2)}")
    print(f"Compression ratio: {len(test2) / len(encoded2):.2f}x")

    decoded2 = compressor.decode(encoded2)
    print(f"Match: {decoded2 == test2}")

    # Test 3: Random data (should store as-is)
    import random
    random.seed(42)
    test3 = bytes([random.randint(0, 255) for _ in range(100)])
    print(f"\nTest 3 (random) length: {len(test3)}")

    encoded3 = compressor.encode(test3)
    print(f"Encoded length: {len(encoded3)}")

    decoded3 = compressor.decode(encoded3)
    print(f"Match: {decoded3 == test3}")

    # Test 4: Empty data
    test4 = b""
    encoded4 = compressor.encode(test4)
    decoded4 = compressor.decode(encoded4)
    print(f"\nTest 4 (empty): Match: {decoded4 == test4}")

    # Test 5: Single byte repeated
    test5 = b"A" * 1000
    print(f"\nTest 5 (1000 'A's) length: {len(test5)}")
    encoded5 = compressor.encode(test5)
    print(f"Encoded length: {len(encoded5)}")
    print(f"Compression ratio: {len(test5) / len(encoded5):.2f}x")
    decoded5 = compressor.decode(encoded5)
    print(f"Match: {decoded5 == test5}")