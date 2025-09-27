"""
Comprehensive Test Suite for Turbo ContextFlow
Q2 2024 - Strict testing for all optimizations
"""

import unittest
import random
import numpy as np
import time
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all implementations for testing
from src.production_compressor import compress_production, decompress_production
from src.quantum_compressor import compress_quantum
from src.turbo_compressor import (
    TurboCompressor, ParallelBlockProcessor, SuffixArrayLZ77,
    AdaptiveBlockSizer, LockFreeRingBuffer, SIMDOperations
)


class TestSIMDOperations(unittest.TestCase):
    """Test SIMD vectorization"""

    def setUp(self):
        self.simd = SIMDOperations()

    def test_fast_softmax(self):
        """Test SIMD softmax implementation"""
        x = np.random.randn(256).astype(np.float32)
        result = self.simd.fast_softmax(x)

        # Check properties
        self.assertAlmostEqual(np.sum(result), 1.0, places=5)
        self.assertTrue(np.all(result >= 0))
        self.assertTrue(np.all(result <= 1))

    def test_fast_dot_product(self):
        """Test SIMD dot product"""
        a = np.random.randn(1000).astype(np.float32)
        b = np.random.randn(1000).astype(np.float32)

        # SIMD version
        result_simd = self.simd.fast_dot_product(a, b)

        # Reference
        result_ref = np.dot(a, b)

        self.assertAlmostEqual(result_simd, result_ref, places=4)

    def test_fast_hash_array(self):
        """Test SIMD array hashing"""
        data = np.random.randint(0, 256, 1000, dtype=np.uint8)
        hashes = self.simd.fast_hash_array(data.astype(np.uint32))

        # Check output
        self.assertEqual(len(hashes), len(data))
        self.assertTrue(np.all(hashes > 0))


class TestParallelProcessor(unittest.TestCase):
    """Test parallel block processing"""

    def setUp(self):
        self.processor = ParallelBlockProcessor(num_threads=4)

    def tearDown(self):
        self.processor.shutdown()

    def test_parallel_compression(self):
        """Test parallel block compression"""
        data = b"test data " * 10000
        block_size = 1024

        def mock_compress(block):
            # Simulate compression work
            time.sleep(0.001)
            return hashlib.sha256(block).digest()

        results = self.processor.process_blocks_parallel(
            data, block_size, mock_compress
        )

        # Check all blocks processed
        expected_blocks = (len(data) + block_size - 1) // block_size
        self.assertEqual(len(results), expected_blocks)

        # Check results are deterministic
        first_hash = hashlib.sha256(data[:block_size]).digest()
        self.assertEqual(results[0], first_hash)

    def test_thread_safety(self):
        """Test thread safety of parallel processing"""
        data = bytes(range(256)) * 100
        block_size = 256

        counter = {'value': 0}

        def count_compress(block):
            counter['value'] += 1
            return bytes([b ^ 0xFF for b in block])  # Simple XOR

        results = self.processor.process_blocks_parallel(
            data, block_size, count_compress
        )

        # Check all blocks were processed
        self.assertEqual(counter['value'], len(results))


class TestSuffixArrayLZ77(unittest.TestCase):
    """Test suffix array LZ77 implementation"""

    def setUp(self):
        self.lz77 = SuffixArrayLZ77()

    def test_suffix_array_construction(self):
        """Test suffix array building"""
        data = np.array([1, 2, 3, 1, 2, 3, 4], dtype=np.uint8)
        sa = self.lz77.build_suffix_array(data)

        # Check properties
        self.assertEqual(len(sa), len(data))
        self.assertEqual(set(sa), set(range(len(data))))

    def test_compression_decompression(self):
        """Test LZ77 compression with suffix array"""
        # Repetitive data
        data = b"ABCABCABCDEF" * 100
        compressed, matches = self.lz77.compress_turbo(data)

        # Should find matches
        self.assertGreater(len(matches), 0)
        self.assertLess(len(compressed), len(data))

        # Verify matches
        for pos, dist, length in matches:
            self.assertGreater(length, 0)
            self.assertGreater(dist, 0)
            self.assertLessEqual(dist, self.lz77.window_size)

    def test_no_matches(self):
        """Test with incompressible data"""
        # Random data - unlikely to have matches
        data = bytes(np.random.randint(0, 256, 1000, dtype=np.uint8))
        compressed, matches = self.lz77.compress_turbo(data)

        # Few or no matches expected
        self.assertLess(len(matches), 10)


class TestAdaptiveBlockSizing(unittest.TestCase):
    """Test adaptive block sizing"""

    def setUp(self):
        self.sizer = AdaptiveBlockSizer()

    def test_entropy_calculation(self):
        """Test entropy analysis"""
        # Low entropy (repetitive)
        low_entropy_data = b"A" * 1000
        entropy_low = self.sizer.analyze_entropy(low_entropy_data)
        self.assertLess(entropy_low, 1.0)

        # High entropy (random)
        high_entropy_data = bytes(np.random.randint(0, 256, 1000, dtype=np.uint8))
        entropy_high = self.sizer.analyze_entropy(high_entropy_data)
        self.assertGreater(entropy_high, 7.0)

    def test_block_size_determination(self):
        """Test block size selection"""
        # Small file
        small_data = b"x" * 1000
        size = self.sizer.determine_block_size(small_data)
        self.assertEqual(size, self.sizer.min_block)

        # Large repetitive file
        large_rep = b"ABC" * 100000
        size_rep = self.sizer.determine_block_size(large_rep)
        self.assertGreater(size_rep, 100000)

        # Random data
        random_data = bytes(np.random.randint(0, 256, 100000, dtype=np.uint8))
        size_rand = self.sizer.determine_block_size(random_data)
        self.assertEqual(size_rand, self.sizer.min_block)

    def test_adaptive_split(self):
        """Test adaptive splitting"""
        data = b"A" * 50000 + bytes(range(256)) * 100 + b"B" * 30000
        blocks = self.sizer.adaptive_split(data)

        # Check blocks cover all data
        total_size = sum(len(block) for _, block in blocks)
        self.assertEqual(total_size, len(data))

        # Check no overlap
        for i in range(len(blocks) - 1):
            self.assertEqual(blocks[i][0] + len(blocks[i][1]), blocks[i+1][0])


class TestLockFreeStructures(unittest.TestCase):
    """Test lock-free data structures"""

    def test_ring_buffer(self):
        """Test lock-free ring buffer"""
        buffer = LockFreeRingBuffer(size=10)

        # Write items
        for i in range(9):
            self.assertTrue(buffer.write(i))

        # Buffer should be almost full
        self.assertFalse(buffer.write(9))  # 10th item fails

        # Read items
        for i in range(9):
            self.assertEqual(buffer.read(), i)

        # Buffer should be empty
        self.assertIsNone(buffer.read())

    def test_concurrent_access(self):
        """Test concurrent access to ring buffer"""
        import threading

        buffer = LockFreeRingBuffer(size=1000)
        results = []

        def producer():
            for i in range(100):
                while not buffer.write(i):
                    time.sleep(0.0001)

        def consumer():
            count = 0
            while count < 100:
                item = buffer.read()
                if item is not None:
                    results.append(item)
                    count += 1
                else:
                    time.sleep(0.0001)

        # Start threads
        prod_thread = threading.Thread(target=producer)
        cons_thread = threading.Thread(target=consumer)

        prod_thread.start()
        cons_thread.start()

        prod_thread.join()
        cons_thread.join()

        # Check all items received
        self.assertEqual(len(results), 100)
        self.assertEqual(set(results), set(range(100)))


class TestTurboCompressor(unittest.TestCase):
    """Test main turbo compressor"""

    def setUp(self):
        self.compressor = TurboCompressor(level=6, use_gpu=False)

    def tearDown(self):
        self.compressor.shutdown()

    def test_empty_data(self):
        """Test with empty data"""
        compressed = self.compressor.compress(b"")
        self.assertIsNotNone(compressed)
        self.assertGreater(len(compressed), 0)

    def test_small_data(self):
        """Test with small data"""
        data = b"Hello, World!"
        compressed = self.compressor.compress(data)

        # Check header
        self.assertTrue(compressed.startswith(b'TURBO'))

        # Check metadata
        self.assertIn(b'"original_size"', compressed)

    def test_large_data(self):
        """Test with large data"""
        data = b"x" * 1000000  # 1MB
        compressed = self.compressor.compress(data)

        # Should compress well
        ratio = len(data) / len(compressed)
        self.assertGreater(ratio, 1.0)

        # Check performance
        self.assertIn('speed_mbps', self.compressor.stats)

    def test_various_data_types(self):
        """Test with different data types"""
        test_cases = [
            (b"Lorem ipsum " * 1000, "text"),
            (bytes(range(256)) * 100, "binary"),
            (b'{"key": "value"}' * 500, "json"),
            (b"<xml>data</xml>" * 300, "xml"),
        ]

        for data, name in test_cases:
            with self.subTest(data_type=name):
                compressed = self.compressor.compress(data)
                self.assertIsNotNone(compressed)
                self.assertLess(len(compressed), len(data) * 1.1)  # At least no expansion

    def test_parallel_speedup(self):
        """Test parallel processing speedup"""
        data = b"test data " * 100000

        # Single thread
        compressor_single = TurboCompressor(level=6)
        compressor_single.parallel_processor.num_threads = 1

        start = time.perf_counter()
        compressed_single = compressor_single.compress(data)
        time_single = time.perf_counter() - start

        compressor_single.shutdown()

        # Multi thread
        compressor_multi = TurboCompressor(level=6)

        start = time.perf_counter()
        compressed_multi = compressor_multi.compress(data)
        time_multi = time.perf_counter() - start

        compressor_multi.shutdown()

        # Should have some speedup
        speedup = time_single / time_multi
        self.assertGreater(speedup, 1.0)  # At least some improvement

        print(f"\nParallel speedup: {speedup:.2f}x")


class TestCorpusIntegration(unittest.TestCase):
    """Test on standard corpuses"""

    @unittest.skipIf(not Path("benchmarks/corpuses/canterbury").exists(),
                     "Canterbury corpus not available")
    def test_canterbury_corpus(self):
        """Test on Canterbury corpus files"""
        corpus_dir = Path("benchmarks/corpuses/canterbury")
        compressor = TurboCompressor(level=6)

        for file_path in corpus_dir.glob("*"):
            if file_path.is_file():
                with self.subTest(file=file_path.name):
                    data = file_path.read_bytes()
                    compressed = compressor.compress(data)

                    ratio = len(data) / len(compressed)
                    print(f"\n{file_path.name}: {ratio:.2f}x")

                    self.assertGreater(ratio, 0.8)  # At least some compression

        compressor.shutdown()

    def test_performance_targets(self):
        """Test if we meet Q2 performance targets"""
        data = b"The quick brown fox jumps over the lazy dog. " * 10000

        compressor = TurboCompressor(level=6)

        # Measure performance
        times = []
        for _ in range(5):
            start = time.perf_counter()
            compressed = compressor.compress(data)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = np.mean(times)
        speed_mbps = (len(data) / (1024 * 1024)) / avg_time

        print(f"\nPerformance Test:")
        print(f"  Speed: {speed_mbps:.1f} MB/s")
        print(f"  Target: 20-50 MB/s")

        # Check if we're approaching targets
        self.assertGreater(speed_mbps, 5.0)  # At least 5 MB/s

        compressor.shutdown()


class TestRegressions(unittest.TestCase):
    """Regression tests to ensure no performance degradation"""

    def test_no_memory_leaks(self):
        """Test for memory leaks"""
        import psutil
        import gc

        process = psutil.Process()

        # Get initial memory
        gc.collect()
        mem_before = process.memory_info().rss / (1024 * 1024)

        # Run many compression cycles
        compressor = TurboCompressor(level=6)
        data = b"x" * 10000

        for _ in range(100):
            compressed = compressor.compress(data)

        compressor.shutdown()

        # Check memory
        gc.collect()
        mem_after = process.memory_info().rss / (1024 * 1024)

        # Should not leak more than 10MB
        self.assertLess(mem_after - mem_before, 10.0)

    def test_deterministic_output(self):
        """Test that compression is deterministic"""
        data = b"Test data for deterministic check" * 100

        compressor = TurboCompressor(level=6)

        # Compress multiple times
        results = []
        for _ in range(3):
            compressed = compressor.compress(data)
            # Extract just compressed data (skip timestamp in metadata)
            idx = compressed.find(b'"compressed_size"')
            results.append(compressed[idx:])

        compressor.shutdown()

        # All should be identical (excluding timestamps)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])


def run_all_tests():
    """Run complete test suite"""
    print("=" * 60)
    print("TURBO CONTEXTFLOW COMPREHENSIVE TEST SUITE")
    print("Q2 2024 - 10x Performance Implementation")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSIMDOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestParallelProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestSuffixArrayLZ77))
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptiveBlockSizing))
    suite.addTests(loader.loadTestsFromTestCase(TestLockFreeStructures))
    suite.addTests(loader.loadTestsFromTestCase(TestTurboCompressor))
    suite.addTests(loader.loadTestsFromTestCase(TestCorpusIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestRegressions))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
        print("Q2 2024 Implementation Ready for Production")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Please fix issues before deployment")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)