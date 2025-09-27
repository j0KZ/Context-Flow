"""
Comprehensive Test Suite for ContextFlow
Tests all compressors, edge cases, and features
"""

import pytest
import os
import random
import struct
from typing import List, Tuple
import numpy as np


# Import all compressors
from contextflow.src.turbo_compressor import TurboCompressor
from contextflow.src.quantum_compressor import QuantumCompressor
from contextflow.src.advanced_compressor import AdvancedCompressor
from contextflow.src.config import FeatureFlags, CompressionConfig


class TestDataGenerator:
    """Generate various types of test data"""

    @staticmethod
    def empty_data() -> bytes:
        """Empty data"""
        return b''

    @staticmethod
    def single_byte() -> bytes:
        """Single byte"""
        return b'A'

    @staticmethod
    def repetitive_data(size: int = 1000) -> bytes:
        """Highly repetitive data"""
        return b'A' * size

    @staticmethod
    def random_data(size: int = 1000) -> bytes:
        """Random incompressible data"""
        return os.urandom(size)

    @staticmethod
    def text_data() -> bytes:
        """Typical text data"""
        return b"""The quick brown fox jumps over the lazy dog.
        Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        This is a test of the compression system.""" * 10

    @staticmethod
    def json_data() -> bytes:
        """JSON-like data"""
        return b'{"users": [' + b', '.join([
            b'{"id": %d, "name": "User%d", "active": true}' % (i, i)
            for i in range(100)
        ]) + b']}'

    @staticmethod
    def binary_data() -> bytes:
        """Binary data with structure"""
        data = bytearray()
        for i in range(100):
            data.extend(struct.pack('<IHBf', i, i*2, i%256, float(i)))
        return bytes(data)

    @staticmethod
    def mixed_entropy_data() -> bytes:
        """Data with mixed entropy regions"""
        data = bytearray()
        # Low entropy
        data.extend(b'A' * 500)
        # Medium entropy
        data.extend(b'ABCDEFGHIJ' * 50)
        # High entropy
        data.extend(os.urandom(500))
        # Low entropy again
        data.extend(b'Z' * 500)
        return bytes(data)

    @staticmethod
    def large_file_data(size_mb: int = 1) -> bytes:
        """Generate large file data"""
        chunk = b'The quick brown fox jumps over the lazy dog. ' * 100
        chunks_needed = (size_mb * 1024 * 1024) // len(chunk)
        return chunk * chunks_needed


class TestComprehensive:
    """Comprehensive test suite for all compressors"""

    @pytest.fixture
    def compressors(self):
        """Get all compressor instances"""
        return [
            TurboCompressor(),
            QuantumCompressor(),
            AdvancedCompressor()
        ]

    @pytest.fixture
    def test_data_sets(self):
        """Get all test data sets"""
        gen = TestDataGenerator()
        return [
            ('empty', gen.empty_data()),
            ('single_byte', gen.single_byte()),
            ('repetitive_small', gen.repetitive_data(100)),
            ('repetitive_large', gen.repetitive_data(10000)),
            ('random_small', gen.random_data(100)),
            ('random_large', gen.random_data(10000)),
            ('text', gen.text_data()),
            ('json', gen.json_data()),
            ('binary', gen.binary_data()),
            ('mixed_entropy', gen.mixed_entropy_data()),
        ]

    def test_basic_compression(self, compressors, test_data_sets):
        """Test basic compression/decompression for all data types"""
        for compressor in compressors:
            for name, data in test_data_sets:
                # Compress
                compressed = compressor.compress(data)
                assert isinstance(compressed, bytes), f"{compressor.__class__.__name__} failed on {name}"

                # Decompress
                decompressed = compressor.decompress(compressed)
                assert decompressed == data, f"{compressor.__class__.__name__} integrity failed on {name}"

    def test_compression_ratio(self, compressors):
        """Test that repetitive data achieves good compression"""
        gen = TestDataGenerator()
        repetitive = gen.repetitive_data(10000)

        for compressor in compressors:
            compressed = compressor.compress(repetitive)
            ratio = len(repetitive) / len(compressed)
            assert ratio > 5, f"{compressor.__class__.__name__} poor compression ratio: {ratio}"

    def test_incompressible_data(self, compressors):
        """Test handling of incompressible random data"""
        gen = TestDataGenerator()
        random_data = gen.random_data(1000)

        for compressor in compressors:
            compressed = compressor.compress(random_data)
            # Should not expand too much (allow 10% expansion)
            assert len(compressed) < len(random_data) * 1.1

            # Must decompress correctly
            decompressed = compressor.decompress(compressed)
            assert decompressed == random_data

    def test_large_files(self, compressors):
        """Test large file handling (>64KB threshold)"""
        gen = TestDataGenerator()
        large_data = gen.large_file_data(1)  # 1MB

        for compressor in compressors:
            # This should use chunked processing
            compressed = compressor.compress(large_data)
            decompressed = compressor.decompress(compressed)
            assert decompressed == large_data

    def test_edge_cases(self, compressors):
        """Test various edge cases"""
        test_cases = [
            b'',  # Empty
            b'\x00',  # Null byte
            b'\xff',  # Max byte
            b'\x00' * 1000,  # All nulls
            b'\xff' * 1000,  # All max bytes
            bytes(range(256)),  # All byte values
            bytes(range(256)) * 10,  # Repeated byte sequence
        ]

        for compressor in compressors:
            for data in test_cases:
                compressed = compressor.compress(data)
                decompressed = compressor.decompress(compressed)
                assert decompressed == data

    def test_progress_callback(self):
        """Test progress callback functionality"""
        gen = TestDataGenerator()
        large_data = gen.large_file_data(1)

        progress_reports = []

        def progress_callback(current, total, message):
            progress_reports.append((current, total, message))

        compressor = TurboCompressor()
        compressed = compressor.compress(large_data, progress_callback)

        # Should have received progress reports for large file
        if FeatureFlags.USE_CHUNKED_PROCESSING:
            assert len(progress_reports) > 0

    def test_concurrent_compression(self, compressors):
        """Test thread safety with concurrent operations"""
        import threading
        gen = TestDataGenerator()
        test_data = gen.text_data()

        def compress_decompress(compressor, data, results, index):
            compressed = compressor.compress(data)
            decompressed = compressor.decompress(compressed)
            results[index] = (compressed, decompressed)

        for compressor in compressors:
            results = [None] * 10
            threads = []

            for i in range(10):
                thread = threading.Thread(
                    target=compress_decompress,
                    args=(compressor, test_data, results, i)
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All results should be valid
            for compressed, decompressed in results:
                assert decompressed == test_data

    def test_memory_usage(self):
        """Test that memory usage stays within limits"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        gen = TestDataGenerator()
        large_data = gen.large_file_data(10)  # 10MB

        compressor = TurboCompressor()
        compressed = compressor.compress(large_data)

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Should not use more than 100MB for 10MB file
        assert memory_increase < 100, f"Excessive memory usage: {memory_increase}MB"

    @pytest.mark.parametrize("size", [0, 1, 10, 100, 1024, 65536, 100000])
    def test_various_sizes(self, compressors, size):
        """Test compression with various data sizes"""
        data = os.urandom(size)

        for compressor in compressors:
            compressed = compressor.compress(data)
            decompressed = compressor.decompress(compressed)
            assert decompressed == data, f"Failed at size {size}"

    def test_corrupted_data_handling(self, compressors):
        """Test handling of corrupted compressed data"""
        gen = TestDataGenerator()
        data = gen.text_data()

        for compressor in compressors:
            compressed = compressor.compress(data)

            # Corrupt the data
            corrupted = bytearray(compressed)
            if len(corrupted) > 10:
                corrupted[10] ^= 0xFF  # Flip bits

            # Should either decompress with error recovery or raise exception
            try:
                decompressed = compressor.decompress(bytes(corrupted))
                # If it succeeds, it should be due to error recovery
                # We can't assert exact equality due to corruption
            except Exception:
                # Expected for corrupted data without error recovery
                pass


class TestFeatureFlags:
    """Test feature flag system"""

    def test_safe_mode(self):
        """Test that safe mode disables experimental features"""
        FeatureFlags.safe_mode()
        assert not FeatureFlags.USE_CUSTOM_LZ77
        assert not FeatureFlags.USE_HYBRID_ANS
        assert not FeatureFlags.USE_GPU
        assert FeatureFlags.ENABLE_FALLBACKS

    def test_experimental_mode(self):
        """Test that experimental mode enables all features"""
        FeatureFlags.experimental_mode()
        assert FeatureFlags.USE_CUSTOM_LZ77
        assert FeatureFlags.USE_HYBRID_ANS
        assert FeatureFlags.USE_GPU

    def test_config_validation(self):
        """Test configuration validation"""
        assert CompressionConfig.validate()

        # Test invalid config
        original = CompressionConfig.MIN_BLOCK_SIZE
        CompressionConfig.MIN_BLOCK_SIZE = -1
        assert not CompressionConfig.validate()
        CompressionConfig.MIN_BLOCK_SIZE = original


class TestChunkedProcessing:
    """Test chunked processing for large files"""

    def test_chunked_format(self):
        """Test chunked format encoding/decoding"""
        from contextflow.src.chunked_processor import ChunkedProcessor

        processor = ChunkedProcessor()
        data = b'A' * 100000  # Large enough to trigger chunking

        def simple_compress(chunk):
            return b'COMP' + chunk

        def simple_decompress(chunk):
            if chunk.startswith(b'COMP'):
                return chunk[4:]
            return chunk

        # Test compression
        compressed = processor.compress_chunked(data, simple_compress)
        assert compressed.startswith(b'CHNK')

        # Test decompression
        decompressed = processor.decompress_chunked(compressed, simple_decompress)
        assert decompressed == data

    def test_adaptive_chunking(self):
        """Test adaptive chunk size determination"""
        from contextflow.src.chunked_processor import AdaptiveChunker

        chunker = AdaptiveChunker()

        # High entropy data should get smaller chunks
        random_data = os.urandom(10000)
        chunk_size_random = chunker.determine_chunk_size(random_data)

        # Low entropy data should get larger chunks
        repetitive_data = b'A' * 10000
        chunk_size_repetitive = chunker.determine_chunk_size(repetitive_data)

        assert chunk_size_random < chunk_size_repetitive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])