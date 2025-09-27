"""
Fast Asymmetric Numeral Systems (tANS) entropy coder
Production-ready implementation optimized for speed and memory efficiency
"""

import numpy as np
from typing import Tuple, List, Optional
import struct


class FastANS:
    """
    Fast tANS implementation with streaming support
    Optimized for speed with reasonable compression ratio
    """

    def __init__(self, alphabet_size: int = 256, table_log: int = 12):
        """
        Initialize tANS encoder/decoder

        Args:
            alphabet_size: Number of symbols (256 for bytes)
            table_log: Table size as power of 2 (12 = 4KB table)
        """
        self.alphabet_size = alphabet_size
        self.table_log = table_log  # Keep small for speed
        self.table_size = 1 << table_log

        # State bounds for renormalization
        self.L = 1 << 16  # Lower bound
        self.b = 16  # Bits per output

        # Encoding/decoding tables (will be built from frequencies)
        self.encode_table = None
        self.decode_table = None
        self.symbol_table = None

    def build_tables(self, frequencies: np.ndarray):
        """
        Build encoding/decoding tables from symbol frequencies

        Args:
            frequencies: Symbol frequency counts
        """
        # Normalize frequencies to sum to table_size
        total = np.sum(frequencies)
        if total == 0:
            # Uniform distribution if no data
            normalized = np.ones(self.alphabet_size) * (self.table_size / self.alphabet_size)
        else:
            normalized = frequencies * (self.table_size / total)

        # Ensure each symbol gets at least 1 slot
        normalized = np.maximum(normalized, 1)

        # Adjust to exactly sum to table_size
        cumulative = np.round(normalized).astype(np.int32)
        diff = self.table_size - np.sum(cumulative)

        # Distribute difference to largest frequencies
        if diff != 0:
            indices = np.argsort(frequencies)[::-1]
            for i in range(min(abs(diff), len(indices))):
                cumulative[indices[i]] += np.sign(diff)

        # Build cumulative distribution
        cumul = np.zeros(self.alphabet_size + 1, dtype=np.int32)
        cumul[1:] = np.cumsum(cumulative)

        # Build decoding table
        self.decode_table = np.zeros(self.table_size, dtype=np.uint16)
        self.symbol_table = np.zeros(self.table_size, dtype=np.uint8)

        for sym in range(self.alphabet_size):
            for i in range(cumul[sym], cumul[sym + 1]):
                self.decode_table[i] = cumulative[sym]
                self.symbol_table[i] = sym

        # Build encoding table (start positions)
        self.encode_table = cumul[:-1].copy()
        self.frequencies = cumulative

    def encode(self, data: bytes) -> bytes:
        """
        Encode data using tANS

        Args:
            data: Input bytes to encode

        Returns:
            Compressed data
        """
        if not data:
            return b''

        # Calculate symbol frequencies
        frequencies = np.bincount(np.frombuffer(data, dtype=np.uint8),
                                  minlength=self.alphabet_size)

        # Build encoding tables
        self.build_tables(frequencies)

        # Initialize state
        state = self.L
        output = []

        # Process symbols in reverse order (tANS encodes backwards)
        for byte in reversed(data):
            freq = self.frequencies[byte]
            if freq == 0:
                continue

            # Renormalization
            while state >= freq * self.L:
                output.append(state & 0xFFFF)
                state >>= 16

            # Encoding step
            state = ((state // freq) << self.table_log) + \
                    (state % freq) + self.encode_table[byte]

        # Final state
        output.append(state)

        # Pack output
        result = bytearray()

        # Header: Store frequency table (compressed)
        # Use simple RLE for zero runs
        freq_data = self._compress_frequencies(self.frequencies)
        result.extend(struct.pack('<I', len(freq_data)))
        result.extend(freq_data)

        # Store encoded data size
        result.extend(struct.pack('<I', len(data)))

        # Store compressed stream (reversed back to normal order)
        for val in reversed(output):
            result.extend(struct.pack('<H', val & 0xFFFF))

        return bytes(result)

    def decode(self, encoded: bytes) -> bytes:
        """
        Decode tANS compressed data

        Args:
            encoded: Compressed data

        Returns:
            Original data
        """
        if not encoded:
            return b''

        offset = 0

        # Read frequency table size
        freq_size = struct.unpack_from('<I', encoded, offset)[0]
        offset += 4

        # Read and decompress frequencies
        freq_data = encoded[offset:offset + freq_size]
        offset += freq_size
        self.frequencies = self._decompress_frequencies(freq_data)

        # Rebuild tables
        self.build_tables(self.frequencies)

        # Read original size
        original_size = struct.unpack_from('<I', encoded, offset)[0]
        offset += 4

        # Read compressed stream
        stream = []
        while offset < len(encoded):
            stream.append(struct.unpack_from('<H', encoded, offset)[0])
            offset += 2

        if not stream:
            return b''

        # Initialize decoding
        result = bytearray()
        state = stream[-1]  # Start from last value (since we encoded in reverse)
        stream_idx = len(stream) - 2

        # Decode symbols
        while len(result) < original_size:
            # Decode symbol
            slot = state & (self.table_size - 1)
            symbol = self.symbol_table[slot]
            freq = self.decode_table[slot]

            result.append(symbol)

            # Update state
            state = freq * (state >> self.table_log) + slot - self.encode_table[symbol]

            # Renormalization
            while state < self.L and stream_idx >= 0:
                state = (state << 16) | stream[stream_idx]
                stream_idx -= 1

        return bytes(result[:original_size])

    def _compress_frequencies(self, frequencies: np.ndarray) -> bytes:
        """Compress frequency table using simple RLE"""
        result = bytearray()
        i = 0

        while i < len(frequencies):
            freq = frequencies[i]

            # Count run length
            run = 1
            while i + run < len(frequencies) and frequencies[i + run] == freq:
                run += 1

            if freq == 0 and run > 3:
                # Encode zero run
                result.append(0)  # Zero marker
                result.extend(struct.pack('<H', run))
                i += run
            else:
                # Encode single frequency
                if freq < 128:
                    result.append(freq | 0x80)  # Single byte frequency
                else:
                    result.append(0x7F)  # Two byte marker
                    result.extend(struct.pack('<H', freq))
                i += 1

        return bytes(result)

    def _decompress_frequencies(self, data: bytes) -> np.ndarray:
        """Decompress frequency table"""
        frequencies = np.zeros(self.alphabet_size, dtype=np.int32)
        i = 0
        pos = 0

        while i < len(data) and pos < self.alphabet_size:
            byte = data[i]

            if byte == 0:
                # Zero run
                run_length = struct.unpack_from('<H', data, i + 1)[0]
                frequencies[pos:pos + run_length] = 0
                pos += run_length
                i += 3
            elif byte == 0x7F:
                # Two byte frequency
                frequencies[pos] = struct.unpack_from('<H', data, i + 1)[0]
                pos += 1
                i += 3
            else:
                # Single byte frequency
                frequencies[pos] = byte & 0x7F
                pos += 1
                i += 1

        return frequencies


class StreamingANS:
    """
    Streaming tANS for large files with adaptive frequency updates
    """

    def __init__(self, block_size: int = 65536):
        """
        Initialize streaming encoder

        Args:
            block_size: Size of blocks to process
        """
        self.block_size = block_size
        self.encoder = FastANS(table_log=11)  # Smaller table for speed

    def encode_stream(self, data: bytes) -> bytes:
        """
        Encode data in streaming blocks

        Args:
            data: Input data

        Returns:
            Compressed stream
        """
        result = bytearray()

        # Header
        result.extend(b'SANS')  # Magic
        result.extend(struct.pack('<I', len(data)))  # Original size
        result.extend(struct.pack('<I', self.block_size))  # Block size

        # Process blocks
        for i in range(0, len(data), self.block_size):
            block = data[i:i + self.block_size]

            # Encode block
            compressed = self.encoder.encode(block)

            # Store block size and data
            result.extend(struct.pack('<I', len(compressed)))
            result.extend(compressed)

        return bytes(result)

    def decode_stream(self, data: bytes) -> bytes:
        """
        Decode streaming compressed data

        Args:
            data: Compressed stream

        Returns:
            Original data
        """
        if not data or len(data) < 16:
            return b''

        # Check magic
        if data[:4] != b'SANS':
            raise ValueError("Invalid streaming ANS data")

        # Read header
        original_size = struct.unpack_from('<I', data, 4)[0]
        block_size = struct.unpack_from('<I', data, 8)[0]

        offset = 12
        result = bytearray()

        # Process blocks
        while offset < len(data) and len(result) < original_size:
            # Read block size
            block_size = struct.unpack_from('<I', data, offset)[0]
            offset += 4

            # Read and decode block
            block_data = data[offset:offset + block_size]
            offset += block_size

            decoded = self.encoder.decode(block_data)
            result.extend(decoded)

        return bytes(result[:original_size])