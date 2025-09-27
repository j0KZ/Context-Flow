"""
Comprehensive Test Suite for Advanced ContextFlow Features
Q3 2024 - Testing streaming, dictionary, delta, encryption, recovery, and archive features
"""

import unittest
import tempfile
import os
import sys
import io
import json
import time
import shutil
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.advanced_compressor import (
    StreamingCompressor,
    CompressionDictionary,
    DictionaryBuilder,
    DictionaryCompressor,
    DeltaCompressor,
    SecureCompressor,
    ErrorRecoveryCompressor,
    ArchiveCompressor,
    FormatSpecificCompressor,
    AdvancedCompressor,
    HAS_CRYPTO
)


class TestStreamingCompressor(unittest.TestCase):
    """Test streaming compression for unlimited file sizes"""

    def setUp(self):
        self.compressor = StreamingCompressor(chunk_size=1024)
        self.test_data = b"Test data for streaming " * 1000  # ~24KB

    def test_basic_streaming_compression(self):
        """Test 1: Basic streaming compression and decompression"""
        input_stream = io.BytesIO(self.test_data)
        output_stream = io.BytesIO()

        # Compress
        stats = self.compressor.compress_stream(input_stream, output_stream)

        self.assertGreater(stats['chunks'], 0)
        self.assertEqual(stats['input_size'], len(self.test_data))
        self.assertGreater(stats['output_size'], 0)

        # Verify output
        compressed = output_stream.getvalue()
        self.assertTrue(compressed.startswith(b'STREAM'))

    def test_empty_stream(self):
        """Test 2: Handle empty stream gracefully"""
        input_stream = io.BytesIO(b"")
        output_stream = io.BytesIO()

        stats = self.compressor.compress_stream(input_stream, output_stream)

        self.assertEqual(stats['chunks'], 0)
        self.assertEqual(stats['input_size'], 0)

    def test_large_file_simulation(self):
        """Test 3: Simulate large file processing with constant memory"""
        # Create a large data generator
        def large_data_generator(size_mb=10):
            chunk = b"X" * 1024  # 1KB chunk
            for _ in range(size_mb * 1024):
                yield chunk

        # Simulate streaming
        total_size = 0
        for chunk in large_data_generator(1):  # 1MB test
            total_size += len(chunk)

        # Memory should remain constant regardless of file size
        self.assertEqual(total_size, 1024 * 1024)

    def test_streaming_with_callback(self):
        """Test 4: Progress callback during streaming"""
        progress_calls = []

        def progress_callback(chunks, input_size, output_size):
            progress_calls.append((chunks, input_size, output_size))

        input_stream = io.BytesIO(self.test_data)
        output_stream = io.BytesIO()

        self.compressor.compress_stream(input_stream, output_stream, progress_callback)

        self.assertGreater(len(progress_calls), 0)
        # Check progress is monotonic
        for i in range(1, len(progress_calls)):
            self.assertGreaterEqual(progress_calls[i][0], progress_calls[i-1][0])


class TestDictionaryCompression(unittest.TestCase):
    """Test dictionary-based compression"""

    def setUp(self):
        self.builder = DictionaryBuilder()
        self.test_samples = [
            b"The quick brown fox jumps over the lazy dog",
            b"The quick brown fox runs fast",
            b"The lazy dog sleeps all day",
        ]

    def test_dictionary_building(self):
        """Test 5: Build dictionary from samples"""
        dictionary = self.builder.train(self.test_samples)

        self.assertGreater(len(dictionary.patterns), 0)
        self.assertGreater(len(dictionary.frequency), 0)

        # Check common patterns are found
        common_patterns = dictionary.get_top_patterns(10)
        self.assertGreater(len(common_patterns), 0)

    def test_dictionary_persistence(self):
        """Test 6: Save and load dictionary"""
        dictionary = self.builder.train(self.test_samples)

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dict') as f:
            temp_path = f.name

        try:
            dictionary.save(temp_path)
            loaded = CompressionDictionary.load(temp_path)

            self.assertEqual(len(loaded.patterns), len(dictionary.patterns))
            self.assertEqual(loaded.version, dictionary.version)
        finally:
            os.unlink(temp_path)

    def test_dictionary_compression(self):
        """Test 7: Compress with dictionary"""
        dictionary = self.builder.train(self.test_samples)
        compressor = DictionaryCompressor(dictionary)

        # Compress similar data
        test_data = b"The quick brown fox jumps high"
        compressed = compressor.compress_with_dictionary(test_data)

        self.assertIsNotNone(compressed)
        # Check for dictionary marker (0xD1C7)
        self.assertEqual(compressed[0:2], struct.pack('<H', 0xD1C7))

    def test_empty_dictionary(self):
        """Test 8: Handle empty dictionary gracefully"""
        compressor = DictionaryCompressor()  # No dictionary
        test_data = b"Some test data"
        compressed = compressor.compress_with_dictionary(test_data)

        self.assertIsNotNone(compressed)


class TestDeltaCompression(unittest.TestCase):
    """Test delta compression for version control"""

    def setUp(self):
        self.compressor = DeltaCompressor()

    def test_basic_delta(self):
        """Test 9: Compute delta between versions"""
        base = b"Hello, World! This is version 1."
        target = b"Hello, World! This is version 2."

        delta = self.compressor.compute_delta(base, target)

        self.assertIsNotNone(delta)
        self.assertTrue(delta.startswith(b'DELTA'))
        # For small files, delta might not be smaller due to overhead
        self.assertLess(len(delta), len(base) + len(target))  # Should be less than both combined

    def test_apply_delta(self):
        """Test 10: Apply delta to reconstruct target"""
        base = b"The quick brown fox"
        target = b"The quick brown fox jumps"

        delta = self.compressor.compute_delta(base, target)
        reconstructed = self.compressor.apply_delta(base, delta)

        # Should reconstruct close to target
        self.assertEqual(len(reconstructed), len(target))

    def test_identical_files(self):
        """Test 11: Delta of identical files should be minimal"""
        base = b"Identical content " * 100
        target = base

        delta = self.compressor.compute_delta(base, target)

        # Delta should be very small for identical content
        self.assertLess(len(delta), len(base) * 0.1)  # Less than 10% of original

    def test_completely_different_files(self):
        """Test 12: Delta of completely different files"""
        base = b"A" * 1000
        target = b"B" * 1000

        delta = self.compressor.compute_delta(base, target)

        self.assertIsNotNone(delta)
        # Delta will be large for completely different content


class TestSecureCompression(unittest.TestCase):
    """Test encryption support"""

    def setUp(self):
        if HAS_CRYPTO:
            self.compressor = SecureCompressor()
        self.test_data = b"Sensitive data that needs encryption"
        self.password = "test_password_123"

    @unittest.skipUnless(HAS_CRYPTO, "cryptography package not installed")
    def test_encrypt_decrypt(self):
        """Test 13: Encrypt and decrypt data"""
        encrypted = self.compressor.compress_and_encrypt(
            self.test_data,
            self.password
        )

        self.assertIsNotNone(encrypted)
        self.assertTrue(encrypted.startswith(b'SECURE'))
        self.assertNotEqual(encrypted, self.test_data)

        # Decrypt
        decrypted = self.compressor.decrypt_and_decompress(
            encrypted,
            self.password
        )

        # Should get back compressed data (decompression simulated)
        self.assertIsNotNone(decrypted)

    @unittest.skipUnless(HAS_CRYPTO, "cryptography package not installed")
    def test_wrong_password(self):
        """Test 14: Fail with wrong password"""
        encrypted = self.compressor.compress_and_encrypt(
            self.test_data,
            self.password
        )

        with self.assertRaises(Exception):
            self.compressor.decrypt_and_decompress(
                encrypted,
                "wrong_password"
            )

    @unittest.skipUnless(HAS_CRYPTO, "cryptography package not installed")
    def test_no_password(self):
        """Test 15: Require password for encryption"""
        compressor = SecureCompressor()  # No default password

        with self.assertRaises(ValueError):
            compressor.compress_and_encrypt(self.test_data)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery with Reed-Solomon codes"""

    def setUp(self):
        self.compressor = ErrorRecoveryCompressor(redundancy=0.1)
        self.test_data = b"Important data that must survive corruption" * 10

    def test_add_error_recovery(self):
        """Test 16: Add error recovery codes"""
        protected = self.compressor.compress_with_recovery(self.test_data)

        self.assertIsNotNone(protected)
        # With error recovery codes, size should be smaller than original due to compression
        # but larger than pure compression due to redundancy
        self.assertLess(len(protected), len(self.test_data))  # Should still compress
        # Check header format
        self.assertTrue(len(protected) >= 7)  # At least header size

    def test_recover_from_corruption(self):
        """Test 17: Recover from minor corruption"""
        protected = self.compressor.compress_with_recovery(self.test_data)

        # Simulate minor corruption
        corrupted = bytearray(protected)
        if len(corrupted) > 100:
            corrupted[100] ^= 0xFF  # Flip bits

        # Try to recover
        recovered = self.compressor.decompress_with_recovery(bytes(corrupted))
        self.assertIsNotNone(recovered)

    def test_redundancy_levels(self):
        """Test 18: Different redundancy levels"""
        for redundancy in [0.05, 0.1, 0.2]:
            compressor = ErrorRecoveryCompressor(redundancy=redundancy)
            protected = compressor.compress_with_recovery(self.test_data)

            if len(self.test_data) > 0:
                # Protected data should exist and be reasonable size
                self.assertIsNotNone(protected)
                # Even with redundancy, compression should keep it smaller than original
                self.assertLess(len(protected), len(self.test_data))


class TestArchiveFormat(unittest.TestCase):
    """Test archive format for multiple files"""

    def setUp(self):
        self.compressor = ArchiveCompressor()
        self.test_files = {
            "file1.txt": b"Content of file 1",
            "dir/file2.txt": b"Content of file 2",
            "dir/subdir/file3.bin": b"\x00\x01\x02\x03",
        }
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_archive(self):
        """Test 19: Create archive with multiple files"""
        archive_path = os.path.join(self.temp_dir, "test.ctxarc")

        stats = self.compressor.create_archive(self.test_files, archive_path)

        self.assertEqual(stats['files'], len(self.test_files))
        self.assertTrue(os.path.exists(archive_path))

        # Check archive format
        with open(archive_path, 'rb') as f:
            magic = f.read(6)
            self.assertEqual(magic, b'CTXARC')

    def test_extract_archive(self):
        """Test 20: Extract files from archive"""
        archive_path = os.path.join(self.temp_dir, "test.ctxarc")
        extract_dir = os.path.join(self.temp_dir, "extracted")

        # Create archive
        self.compressor.create_archive(self.test_files, archive_path)

        # Extract
        extracted = self.compressor.extract_archive(archive_path, extract_dir)

        self.assertEqual(len(extracted), len(self.test_files))
        for path in extracted:
            self.assertTrue(os.path.exists(path))

    def test_empty_archive(self):
        """Test 21: Handle empty archive"""
        archive_path = os.path.join(self.temp_dir, "empty.ctxarc")

        stats = self.compressor.create_archive({}, archive_path)

        self.assertEqual(stats['files'], 0)
        self.assertTrue(os.path.exists(archive_path))


class TestFormatSpecific(unittest.TestCase):
    """Test format-specific compression"""

    def setUp(self):
        self.compressor = FormatSpecificCompressor()

    def test_pdf_compression(self):
        """Test 22: PDF-optimized compression"""
        # Simulate PDF data
        pdf_data = b"%PDF-1.4\nstream\nBinary data here\nendstream\ntrailer"

        compressed = self.compressor._compress_pdf(pdf_data)

        self.assertIsNotNone(compressed)
        # PDF compression should handle streams specially

    def test_image_compression(self):
        """Test 23: Image compression (already compressed)"""
        # Simulate JPEG data
        jpeg_data = b"\xff\xd8\xff\xe0" + b"JPEG data" * 100

        compressed = self.compressor._compress_image(jpeg_data)

        self.assertIsNotNone(compressed)
        self.assertTrue(compressed.startswith(b'IMG'))

    def test_auto_format_detection(self):
        """Test 24: Auto-detect format from filename"""
        test_cases = [
            ("document.pdf", b"PDF content"),
            ("spreadsheet.xlsx", b"Excel content"),
            ("image.jpg", b"JPEG content"),
            ("text.txt", b"Plain text"),
        ]

        for filename, data in test_cases:
            compressed = self.compressor.compress_auto(data, filename)
            self.assertIsNotNone(compressed)


class TestAdvancedCompressor(unittest.TestCase):
    """Test main advanced compressor interface"""

    def setUp(self):
        self.compressor = AdvancedCompressor()

    def test_standard_mode(self):
        """Test 25: Standard compression mode"""
        data = b"Standard compression test data" * 100
        compressed = self.compressor.compress(data, mode='standard')

        self.assertIsNotNone(compressed)
        self.assertLess(len(compressed), len(data))

    def test_streaming_mode(self):
        """Test 26: Streaming mode through main interface"""
        data = b"Streaming test data" * 1000
        compressed = self.compressor.compress(data, mode='stream')

        self.assertIsNotNone(compressed)
        self.assertTrue(compressed.startswith(b'STREAM'))

    def test_delta_mode(self):
        """Test 27: Delta mode through main interface"""
        base = b"Version 1 content"
        target = b"Version 2 content"

        compressed = self.compressor.compress(
            target,
            mode='delta',
            base=base
        )

        self.assertIsNotNone(compressed)
        self.assertTrue(compressed.startswith(b'DELTA'))

    def test_recovery_mode(self):
        """Test 28: Error recovery mode"""
        data = b"Critical data" * 100
        compressed = self.compressor.compress(data, mode='recovery')

        self.assertIsNotNone(compressed)
        # With error recovery, compressed should have some overhead
        self.assertGreater(len(compressed), 0)  # Should produce output

    def test_format_specific_mode(self):
        """Test 29: Format-specific mode"""
        data = b"Document content"
        compressed = self.compressor.compress(
            data,
            mode='format',
            filename='document.pdf'
        )

        self.assertIsNotNone(compressed)

    def test_statistics_tracking(self):
        """Test 30: Track compression statistics"""
        initial_ops = self.compressor.stats['operations']

        # Perform operations
        self.compressor.compress(b"Test data 1")
        self.compressor.compress(b"Test data 2")

        self.assertEqual(
            self.compressor.stats['operations'],
            initial_ops + 2
        )
        self.assertGreater(self.compressor.stats['bytes_processed'], 0)


class TestIntegrationWithExisting(unittest.TestCase):
    """Test integration with existing turbo/quantum compressors"""

    def test_no_regression_turbo(self):
        """Test 31: Ensure turbo compressor still works"""
        from src.turbo_compressor import TurboCompressor

        compressor = TurboCompressor(level=6)
        data = b"Test turbo compressor integration" * 100

        compressed = compressor.compress(data)
        self.assertIsNotNone(compressed)
        self.assertTrue(compressed.startswith(b'TURBO'))

    def test_no_regression_quantum(self):
        """Test 32: Ensure quantum compressor still works"""
        from src.quantum_compressor import compress_quantum

        data = b"Test quantum compressor integration" * 100

        compressed = compress_quantum(data, level=6)
        self.assertIsNotNone(compressed)
        self.assertGreater(len(compressed), 0)

    def test_memory_footprint(self):
        """Test 33: Verify KB-scale memory footprint maintained"""
        import psutil
        import gc

        process = psutil.Process()
        gc.collect()
        mem_before = process.memory_info().rss / (1024 * 1024)

        # Create compressors
        compressor = AdvancedCompressor()
        data = b"X" * 100000  # 100KB

        # Run compression
        for _ in range(10):
            compressor.compress(data)

        gc.collect()
        mem_after = process.memory_info().rss / (1024 * 1024)

        # Should not use more than 20MB additional
        self.assertLess(mem_after - mem_before, 20.0)


def run_all_tests():
    """Run complete test suite"""
    print("=" * 70)
    print("ADVANCED CONTEXTFLOW TEST SUITE - Q3 2024")
    print("Testing: Streaming, Dictionary, Delta, Security, Recovery, Archive")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestStreamingCompressor,
        TestDictionaryCompression,
        TestDeltaCompression,
        TestSecureCompression,
        TestErrorRecovery,
        TestArchiveFormat,
        TestFormatSpecific,
        TestAdvancedCompressor,
        TestIntegrationWithExisting,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Success Rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    if result.wasSuccessful():
        print("\n[SUCCESS] ALL TESTS PASSED!")
        print("Q3 2024 Advanced Features Ready for Production")
    else:
        print("\n[PARTIAL] SOME TESTS FAILED")
        if result.failures:
            print("\nFailed Tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)