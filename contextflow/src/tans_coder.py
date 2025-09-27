"""
tANS (tabled Asymmetric Numeral Systems) entropy coder
Fast implementation with adaptive probability tables
"""

import numpy as np
from typing import List, Tuple, Optional
import struct
from collections import deque

class TANSEncoder:
    """
    tANS encoder with 12-bit states for good compression/speed tradeoff
    """

    def __init__(self, state_bits: int = 12):
        self.state_bits = state_bits
        self.state_size = 1 << state_bits
        self.state_mask = self.state_size - 1

        self.encode_table = None
        self.decode_table = None
        self.symbol_table = None

        self.state = self.state_size

        self.output_buffer = bytearray()
        self.stream_buffers = [bytearray() for _ in range(4)]
        self.current_stream = 0

        self.fallback_huffman = HuffmanCoder()

    def build_tables(self, probabilities: np.ndarray):
        """Build encoding/decoding tables from probability distribution"""
        probabilities = np.clip(probabilities, 1e-10, 1.0)
        probabilities /= np.sum(probabilities)

        frequencies = np.round(probabilities * self.state_size).astype(np.int32)
        frequencies = np.maximum(frequencies, 1)

        total = np.sum(frequencies)
        if total != self.state_size:
            diff = self.state_size - total
            max_idx = np.argmax(frequencies)
            frequencies[max_idx] += diff

        self._build_encode_table(frequencies)
        self._build_decode_table(frequencies)

    def _build_encode_table(self, frequencies: np.ndarray):
        """Build encoding table"""
        self.encode_table = np.zeros((256, self.state_size), dtype=np.uint16)
        self.symbol_starts = np.zeros(256, dtype=np.int32)

        cumulative = 0
        for symbol in range(256):
            self.symbol_starts[symbol] = cumulative
            freq = frequencies[symbol]

            if freq > 0:
                for i in range(freq):
                    state = cumulative + i
                    self.encode_table[symbol, state] = self.state_size + i

            cumulative += freq

    def _build_decode_table(self, frequencies: np.ndarray):
        """Build decoding table"""
        self.decode_table = np.zeros(self.state_size * 2, dtype=np.uint8)
        self.next_state_table = np.zeros(self.state_size * 2, dtype=np.uint16)

        state_alloc = np.zeros(256, dtype=np.int32)

        for state in range(self.state_size, self.state_size * 2):
            slot = state - self.state_size

            cumulative = 0
            for symbol in range(256):
                if cumulative + frequencies[symbol] > slot:
                    self.decode_table[state] = symbol
                    self.next_state_table[state] = state_alloc[symbol] + self.symbol_starts[symbol]
                    state_alloc[symbol] += 1
                    break
                cumulative += frequencies[symbol]

    def encode_symbol(self, symbol: int):
        """Encode a single symbol"""
        if self.encode_table is None:
            raise ValueError("Tables not built")

        while self.state >= self.state_size * 2:
            self.output_buffer.append(self.state & 0xFF)
            self.state >>= 8

        next_state_base = self.encode_table[symbol, self.state & self.state_mask]
        self.state = next_state_base + (self.state >> self.state_bits << self.state_bits)

    def encode_block(self, data: bytes, probabilities: np.ndarray) -> bytes:
        """Encode a block of data with given probabilities"""
        if np.max(probabilities) > 0.99:
            return self.fallback_huffman.encode(data, probabilities)

        self.build_tables(probabilities)
        self.state = self.state_size
        self.output_buffer.clear()

        for byte in data:
            self.encode_symbol(byte)

        while self.state > 1:
            self.output_buffer.append(self.state & 0xFF)
            self.state >>= 8

        return bytes(self.output_buffer)

    def encode_interleaved(self, data: bytes, probabilities: np.ndarray) -> List[bytes]:
        """Encode with interleaved streams for parallel decoding"""
        self.build_tables(probabilities)

        streams = [bytearray() for _ in range(4)]
        states = [self.state_size] * 4

        for i, byte in enumerate(data):
            stream_idx = i % 4
            state = states[stream_idx]

            while state >= self.state_size * 2:
                streams[stream_idx].append(state & 0xFF)
                state >>= 8

            next_state_base = self.encode_table[byte, state & self.state_mask]
            state = next_state_base + (state >> self.state_bits << self.state_bits)
            states[stream_idx] = state

        for i in range(4):
            while states[i] > 1:
                streams[i].append(states[i] & 0xFF)
                states[i] >>= 8

        return [bytes(s) for s in streams]


class TANSDecoder:
    """tANS decoder with table-based decoding"""

    def __init__(self, state_bits: int = 12):
        self.state_bits = state_bits
        self.state_size = 1 << state_bits
        self.state_mask = self.state_size - 1

        self.decode_table = None
        self.next_state_table = None

        self.fallback_huffman = HuffmanCoder()

    def build_tables(self, probabilities: np.ndarray):
        """Build decoding tables from probability distribution"""
        encoder = TANSEncoder(self.state_bits)
        encoder.build_tables(probabilities)

        self.decode_table = encoder.decode_table
        self.next_state_table = encoder.next_state_table

    def decode_block(self, encoded: bytes, length: int, probabilities: np.ndarray) -> bytes:
        """Decode a block of encoded data"""
        if not encoded or length == 0:
            return b''

        if np.max(probabilities) > 0.99:
            return self.fallback_huffman.decode(encoded, length, probabilities)

        self.build_tables(probabilities)

        result = bytearray()
        state = self.state_size
        input_pos = 0

        while len(result) < length and input_pos < len(encoded):
            while state < self.state_size * 2 and input_pos < len(encoded):
                state = (state << 8) | encoded[input_pos]
                input_pos += 1

            if state >= len(self.decode_table):
                # State overflow, reset
                state = self.state_size
                continue

            symbol = self.decode_table[state]
            result.append(symbol)
            state = self.next_state_table[state]

            if state == 0:
                state = self.state_size

        return bytes(result[:length])

    def decode_interleaved(self, streams: List[bytes], length: int, probabilities: np.ndarray) -> bytes:
        """Decode interleaved streams"""
        self.build_tables(probabilities)

        results = []
        for stream in streams:
            partial = self.decode_block(stream, (length + 3) // 4, probabilities)
            results.append(partial)

        interleaved = bytearray()
        for i in range(length):
            stream_idx = i % 4
            byte_idx = i // 4
            if byte_idx < len(results[stream_idx]):
                interleaved.append(results[stream_idx][byte_idx])

        return bytes(interleaved[:length])


class HuffmanCoder:
    """Fallback Huffman coder for incompressible data"""

    def __init__(self):
        self.codes = {}
        self.tree = None

    def build_codes(self, probabilities: np.ndarray):
        """Build Huffman codes from probabilities"""
        heap = []
        for symbol, prob in enumerate(probabilities):
            if prob > 0:
                heap.append((prob, symbol))

        heap.sort()

        while len(heap) > 1:
            prob1, left = heap.pop(0)
            prob2, right = heap.pop(0)

            combined = (prob1 + prob2, (left, right))
            heap.append(combined)
            heap.sort()

        if heap:
            self.tree = heap[0][1]
            self._assign_codes(self.tree, '')

    def _assign_codes(self, node, code: str):
        """Recursively assign Huffman codes"""
        if isinstance(node, int):
            self.codes[node] = code if code else '0'
        else:
            left, right = node
            self._assign_codes(left, code + '0')
            self._assign_codes(right, code + '1')

    def encode(self, data: bytes, probabilities: np.ndarray) -> bytes:
        """Encode data using Huffman coding"""
        self.build_codes(probabilities)

        bits = []
        for byte in data:
            if byte in self.codes:
                bits.extend(self.codes[byte])
            else:
                bits.extend('0' * 8)

        while len(bits) % 8 != 0:
            bits.append('0')

        result = bytearray()
        for i in range(0, len(bits), 8):
            byte_bits = ''.join(bits[i:i+8])
            result.append(int(byte_bits, 2))

        return bytes(result)

    def decode(self, encoded: bytes, length: int, probabilities: np.ndarray) -> bytes:
        """Decode Huffman encoded data"""
        self.build_codes(probabilities)

        if not self.tree:
            return b'\x00' * length

        bits = []
        for byte in encoded:
            bits.extend(format(byte, '08b'))

        result = bytearray()
        current = self.tree
        for bit in bits:
            if len(result) >= length:
                break

            if isinstance(current, int):
                result.append(current)
                current = self.tree

            if not isinstance(current, int):
                if bit == '0':
                    current = current[0]
                else:
                    current = current[1]

                if isinstance(current, int):
                    result.append(current)
                    current = self.tree

        return bytes(result[:length])


class AdaptiveANS:
    """Adaptive tANS with probability updates"""

    def __init__(self, window_size: int = 4096):
        self.window_size = window_size
        self.encoder = TANSEncoder()
        self.decoder = TANSDecoder()

        self.symbol_counts = np.ones(256, dtype=np.float32)
        self.total_count = 256.0
        self.history = deque(maxlen=window_size)

    def update_probabilities(self, symbol: int):
        """Update probability model with new symbol"""
        self.symbol_counts[symbol] += 1
        self.total_count += 1

        self.history.append(symbol)

        if len(self.history) == self.window_size:
            old_symbol = self.history[0]
            self.symbol_counts[old_symbol] = max(1, self.symbol_counts[old_symbol] - 1)
            self.total_count = max(256, self.total_count - 1)

    def get_probabilities(self) -> np.ndarray:
        """Get current probability distribution"""
        return self.symbol_counts / self.total_count

    def encode_adaptive(self, data: bytes) -> bytes:
        """Encode with adaptive probabilities"""
        output = bytearray()
        block_size = 1024

        for i in range(0, len(data), block_size):
            block = data[i:i + block_size]

            probs = self.get_probabilities()

            encoded = self.encoder.encode_block(block, probs)

            output.extend(struct.pack('<H', len(encoded)))
            output.extend(encoded)

            for byte in block:
                self.update_probabilities(byte)

        return bytes(output)

    def decode_adaptive(self, encoded: bytes, original_length: int) -> bytes:
        """Decode with adaptive probabilities"""
        result = bytearray()
        pos = 0

        while pos < len(encoded) and len(result) < original_length:
            if pos + 2 > len(encoded):
                break

            block_len = struct.unpack('<H', encoded[pos:pos+2])[0]
            pos += 2

            if pos + block_len > len(encoded):
                break

            block_data = encoded[pos:pos + block_len]
            pos += block_len

            probs = self.get_probabilities()

            remaining = original_length - len(result)
            decode_len = min(1024, remaining)

            decoded = self.decoder.decode_block(block_data, decode_len, probs)
            result.extend(decoded)

            for byte in decoded:
                self.update_probabilities(byte)

        return bytes(result[:original_length])