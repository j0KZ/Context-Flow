"""
Comprehensive tests for ContextFlow compression system
"""

import unittest
import random
import string
import json
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextflow import compress, decompress
from contextflow.src.data_detector import DataDetector, DataType
from contextflow.src.preprocessing import BurrowsWheelerTransform, SlidingWindowDeduplicator
from contextflow.src.context_model import ContextModel
from contextflow.src.neural_mixer import FastNeuralMixer
from contextflow.src.fast_ans import FastANS, StreamingANS


class TestDataDetector(unittest.TestCase):
    """Test data type detection"""

    def setUp(self):
        self.detector = DataDetector()

    def test_text_detection(self):
        """Test plain text detection"""
        text = b"Hello, this is a plain text file with normal English content."
        data_type, metadata = self.detector.detect(text)
        self.assertEqual(data_type, DataType.TEXT)

    def test_code_detection(self):
        """Test source code detection"""
        code = b"""
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)
"""
        data_type, metadata = self.detector.detect(code)
        self.assertEqual(data_type, DataType.CODE)

    def test_json_detection(self):
        """Test JSON detection"""
        json_data = b'{"name": "test", "value": 123, "nested": {"key": "value"}}'
        data_type, metadata = self.detector.detect(json_data)
        self.assertEqual(data_type, DataType.JSON_DATA)

    def test_xml_detection(self):
        """Test XML detection"""
        xml_data = b'<root><item id="1">Test</item><item id="2">Data</item></root>'
        data_type, metadata = self.detector.detect(xml_data)
        self.assertEqual(data_type, DataType.XML_DATA)

    def test_binary_detection(self):
        """Test binary data detection"""
        binary = bytes(random.randint(0, 255) for _ in range(1000))
        data_type, metadata = self.detector.detect(binary)
        self.assertEqual(data_type, DataType.BINARY)


class TestBWT(unittest.TestCase):
    """Test Burrows-Wheeler Transform"""

    def setUp(self):
        self.bwt = BurrowsWheelerTransform(block_size=1000)

    def test_transform_inverse(self):
        """Test BWT and inverse transform"""
        test_data = b"banana"
        transformed, index = self.bwt.transform(test_data)
        restored = self.bwt.inverse_transform(transformed, [index])
        self.assertEqual(restored, test_data)

    def test_empty_data(self):
        """Test BWT with empty data"""
        transformed, index = self.bwt.transform(b"")
        restored = self.bwt.inverse_transform(transformed, [index])
        self.assertEqual(restored, b"")

    def test_large_data(self):
        """Test BWT with large data"""
        test_data = b"A" * 10000 + b"B" * 5000 + b"C" * 3000
        transformed, indices = self.bwt.transform(test_data)
        restored = self.bwt.inverse_transform(transformed, indices)
        self.assertEqual(restored, test_data)


class TestDeduplication(unittest.TestCase):
    """Test sliding window deduplication"""

    def setUp(self):
        self.dedup = SlidingWindowDeduplicator(window_size=256, min_match=16)

    def test_deduplication(self):
        """Test basic deduplication"""
        data = b"ABCDEFGHIJKLMNOP" * 10
        deduplicated, refs = self.dedup.deduplicate(data)
        self.assertLess(len(deduplicated), len(data))

        restored = self.dedup.restore(deduplicated, refs)
        self.assertEqual(len(restored), len(data))

    def test_no_duplicates(self):
        """Test deduplication with no duplicates"""
        data = bytes(range(256))
        deduplicated, refs = self.dedup.deduplicate(data)
        self.assertEqual(len(deduplicated), len(data))
        self.assertEqual(len(refs), 0)


class TestContextModel(unittest.TestCase):
    """Test context modeling"""

    def setUp(self):
        self.model = ContextModel(max_order=4)

    def test_prediction_update(self):
        """Test context prediction and update"""
        test_sequence = b"ABABABABAB"

        for byte in test_sequence:
            prediction = self.model.predict('text')
            self.assertEqual(len(prediction), 256)
            self.assertAlmostEqual(sum(prediction), 1.0, places=5)
            self.model.update(byte, 'text')

        prediction = self.model.predict('text')
        self.assertTrue(prediction[ord('A')] > 0.3 or prediction[ord('B')] > 0.3)


class TestNeuralMixer(unittest.TestCase):
    """Test neural mixer"""

    def setUp(self):
        self.mixer = FastNeuralMixer(input_size=8, hidden_size=16, output_size=256)

    def test_forward_pass(self):
        """Test neural network forward pass"""
        import numpy as np
        inputs = np.random.randn(8).astype(np.float32)
        output = self.mixer.forward(inputs)

        self.assertEqual(len(output), 256)
        self.assertAlmostEqual(sum(output), 1.0, places=5)
        self.assertTrue(all(0 <= p <= 1 for p in output))

    def test_training(self):
        """Test neural network training"""
        import numpy as np
        inputs = np.random.randn(8).astype(np.float32)
        target = 65

        initial_pred = self.mixer.forward(inputs)
        initial_prob = initial_pred[target]

        for _ in range(10):
            pred = self.mixer.forward(inputs)
            self.mixer.train_step(inputs, target, pred)

        final_pred = self.mixer.forward(inputs)
        final_prob = final_pred[target]

        self.assertGreaterEqual(final_prob, initial_prob * 0.9)


class TestTANS(unittest.TestCase):
    """Test tANS entropy coder"""

    def setUp(self):
        self.ans = FastANS(alphabet_size=256, table_log=11)
        self.streaming = StreamingANS(block_size=1024)

    def test_encode_decode(self):
        """Test tANS encoding and decoding"""
        data = b"Hello, World! This is a test."

        # Test basic ANS
        encoded = self.ans.encode(data)
        decoded = self.ans.decode(encoded)
        self.assertEqual(decoded, data)

        # Test streaming ANS
        stream_encoded = self.streaming.encode_stream(data)
        stream_decoded = self.streaming.decode_stream(stream_encoded)
        self.assertEqual(stream_decoded, data)


class TestEndToEnd(unittest.TestCase):
    """Test end-to-end compression and decompression"""

    def test_text_compression(self):
        """Test compression of text data"""
        text = b"The quick brown fox jumps over the lazy dog. " * 100
        compressed = compress(text)
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, text)
        self.assertLess(len(compressed), len(text))

    def test_json_compression(self):
        """Test compression of JSON data"""
        json_data = json.dumps({
            "users": [{"id": i, "name": f"User{i}", "data": list(range(10))}
                     for i in range(50)]
        }).encode('utf-8')

        compressed = compress(json_data)
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, json_data)

    def test_code_compression(self):
        """Test compression of source code"""
        code = b"""
import numpy as np

def matrix_multiply(A, B):
    '''Multiply two matrices'''
    rows_A, cols_A = A.shape
    rows_B, cols_B = B.shape

    if cols_A != rows_B:
        raise ValueError("Incompatible dimensions")

    C = np.zeros((rows_A, cols_B))

    for i in range(rows_A):
        for j in range(cols_B):
            for k in range(cols_A):
                C[i, j] += A[i, k] * B[k, j]

    return C
""" * 10

        compressed = compress(code)
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, code)

    def test_binary_compression(self):
        """Test compression of binary data"""
        binary = bytes(random.randint(0, 255) for _ in range(1000))
        compressed = compress(binary)
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, binary)

    def test_empty_data(self):
        """Test compression of empty data"""
        compressed = compress(b"")
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, b"")

    def test_fast_mode(self):
        """Test fast mode compression"""
        data = b"Test data for fast mode compression" * 100
        compressed = compress(data, fast_mode=True)
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, data)

    def test_max_compression_mode(self):
        """Test maximum compression mode"""
        data = b"Repetitive data " * 1000
        compressed = compress(data, mode='max_compression')
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, data)

    def test_incompressible_data(self):
        """Test handling of incompressible data"""
        random.seed(42)
        data = bytes(random.randint(0, 255) for _ in range(1000))
        compressed = compress(data)
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, data)


class TestCLI(unittest.TestCase):
    """Test CLI functionality"""

    def test_cli_import(self):
        """Test CLI module imports"""
        from contextflow.cli import CLI
        cli = CLI()
        self.assertIsNotNone(cli.parser)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDataDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestBWT))
    suite.addTests(loader.loadTestsFromTestCase(TestDeduplication))
    suite.addTests(loader.loadTestsFromTestCase(TestContextModel))
    suite.addTests(loader.loadTestsFromTestCase(TestNeuralMixer))
    suite.addTests(loader.loadTestsFromTestCase(TestTANS))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEnd))
    suite.addTests(loader.loadTestsFromTestCase(TestCLI))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)