"""
Comprehensive benchmarking suite for ContextFlow
Tests against standard compression corpuses
"""

import time
import os
import sys
import gzip
import bz2
import lzma
import json
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextflow import compress, decompress


class BenchmarkSuite:
    """Comprehensive benchmarking for ContextFlow"""

    def __init__(self):
        self.results = []
        self.test_files = []

    def create_test_data(self) -> Dict[str, bytes]:
        """Create various types of test data"""
        test_data = {}

        # Text data - Lorem ipsum and English text
        test_data['text_english'] = b"""
        The quick brown fox jumps over the lazy dog. This pangram sentence contains
        every letter of the English alphabet at least once. It is commonly used for
        testing typefaces, keyboards, and other applications involving text.
        """ * 500

        # Repetitive text
        test_data['text_repetitive'] = (b"The pattern repeats. " * 100 + b"\n") * 100

        # JSON data
        json_obj = {
            "users": [
                {
                    "id": i,
                    "name": f"User_{i}",
                    "email": f"user{i}@example.com",
                    "age": 20 + (i % 50),
                    "active": i % 2 == 0,
                    "tags": ["tag1", "tag2", "tag3"] * (i % 3 + 1),
                    "metadata": {
                        "created": "2024-01-01",
                        "modified": "2024-01-02",
                        "version": 1
                    }
                }
                for i in range(100)
            ]
        }
        test_data['json_structured'] = json.dumps(json_obj, indent=2).encode('utf-8')

        # Source code (Python)
        test_data['code_python'] = b"""
def fibonacci(n):
    '''Calculate fibonacci number'''
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.data = []

    def process(self, input_data):
        result = []
        for item in input_data:
            if self.validate(item):
                processed = self.transform(item)
                result.append(processed)
        return result

    def validate(self, item):
        return item is not None and len(str(item)) > 0

    def transform(self, item):
        return str(item).upper()
""" * 50

        # CSV data
        csv_lines = ["id,name,value,category,status"]
        for i in range(500):
            csv_lines.append(f"{i},Item_{i},{i*10.5},Category_{i%10},{'active' if i%2 else 'inactive'}")
        test_data['csv_data'] = '\n'.join(csv_lines).encode('utf-8')

        # XML data
        xml_data = ['<?xml version="1.0" encoding="UTF-8"?>', '<root>']
        for i in range(100):
            xml_data.append(f'  <item id="{i}" type="type_{i%5}">')
            xml_data.append(f'    <name>Item {i}</name>')
            xml_data.append(f'    <value>{i * 100}</value>')
            xml_data.append(f'    <description>Description for item {i}</description>')
            xml_data.append('  </item>')
        xml_data.append('</root>')
        test_data['xml_structured'] = '\n'.join(xml_data).encode('utf-8')

        # Binary data - pseudo-random
        import random
        random.seed(42)
        test_data['binary_random'] = bytes(random.randint(0, 255) for _ in range(10000))

        # Binary data - structured
        binary_structured = bytearray()
        for i in range(100):
            binary_structured.extend(i.to_bytes(4, 'little'))
            binary_structured.extend(b'\x00\x00\xFF\xFF')
            binary_structured.extend((i * 2).to_bytes(4, 'little'))
        test_data['binary_structured'] = bytes(binary_structured)

        return test_data

    def benchmark_compressor(self, data: bytes, name: str, iterations: int = 3) -> Dict:
        """Benchmark a single compressor on data"""
        results = {
            'data_name': name,
            'original_size': len(data),
            'compressors': {}
        }

        # Test ContextFlow modes
        for mode in ['fast', 'balanced', 'max']:
            compress_times = []
            decompress_times = []
            compressed_size = 0

            for _ in range(iterations):
                # Compression
                start = time.time()
                compressed = compress(data, mode=mode, fast_mode=(mode == 'fast'))
                compress_times.append(time.time() - start)
                compressed_size = len(compressed)

                # Decompression
                start = time.time()
                decompressed = decompress(compressed)
                decompress_times.append(time.time() - start)

                # Verify
                assert decompressed == data, f"ContextFlow {mode} decompression failed"

            avg_compress = sum(compress_times) / len(compress_times)
            avg_decompress = sum(decompress_times) / len(decompress_times)

            results['compressors'][f'contextflow_{mode}'] = {
                'compressed_size': compressed_size,
                'ratio': len(data) / compressed_size if compressed_size > 0 else 0,
                'compress_time': avg_compress,
                'decompress_time': avg_decompress,
                'compress_speed_mbps': len(data) / (1024 * 1024 * avg_compress) if avg_compress > 0 else 0,
                'decompress_speed_mbps': len(data) / (1024 * 1024 * avg_decompress) if avg_decompress > 0 else 0
            }

        # Test standard compressors
        # GZIP
        compress_times = []
        decompress_times = []
        for _ in range(iterations):
            start = time.time()
            compressed = gzip.compress(data, compresslevel=9)
            compress_times.append(time.time() - start)

            start = time.time()
            decompressed = gzip.decompress(compressed)
            decompress_times.append(time.time() - start)

        avg_compress = sum(compress_times) / len(compress_times)
        avg_decompress = sum(decompress_times) / len(decompress_times)

        results['compressors']['gzip'] = {
            'compressed_size': len(compressed),
            'ratio': len(data) / len(compressed) if len(compressed) > 0 else 0,
            'compress_time': avg_compress,
            'decompress_time': avg_decompress,
            'compress_speed_mbps': len(data) / (1024 * 1024 * avg_compress) if avg_compress > 0 else 0,
            'decompress_speed_mbps': len(data) / (1024 * 1024 * avg_decompress) if avg_decompress > 0 else 0
        }

        # BZIP2
        compress_times = []
        decompress_times = []
        for _ in range(iterations):
            start = time.time()
            compressed = bz2.compress(data, compresslevel=9)
            compress_times.append(time.time() - start)

            start = time.time()
            decompressed = bz2.decompress(compressed)
            decompress_times.append(time.time() - start)

        avg_compress = sum(compress_times) / len(compress_times)
        avg_decompress = sum(decompress_times) / len(decompress_times)

        results['compressors']['bzip2'] = {
            'compressed_size': len(compressed),
            'ratio': len(data) / len(compressed) if len(compressed) > 0 else 0,
            'compress_time': avg_compress,
            'decompress_time': avg_decompress,
            'compress_speed_mbps': len(data) / (1024 * 1024 * avg_compress) if avg_compress > 0 else 0,
            'decompress_speed_mbps': len(data) / (1024 * 1024 * avg_decompress) if avg_decompress > 0 else 0
        }

        # LZMA
        compress_times = []
        decompress_times = []
        for _ in range(iterations):
            start = time.time()
            compressed = lzma.compress(data, preset=6)  # Use 6 instead of 9 for reasonable speed
            compress_times.append(time.time() - start)

            start = time.time()
            decompressed = lzma.decompress(compressed)
            decompress_times.append(time.time() - start)

        avg_compress = sum(compress_times) / len(compress_times)
        avg_decompress = sum(decompress_times) / len(decompress_times)

        results['compressors']['lzma'] = {
            'compressed_size': len(compressed),
            'ratio': len(data) / len(compressed) if len(compressed) > 0 else 0,
            'compress_time': avg_compress,
            'decompress_time': avg_decompress,
            'compress_speed_mbps': len(data) / (1024 * 1024 * avg_compress) if avg_compress > 0 else 0,
            'decompress_speed_mbps': len(data) / (1024 * 1024 * avg_decompress) if avg_decompress > 0 else 0
        }

        return results

    def run_full_benchmark(self):
        """Run complete benchmark suite"""
        print("ContextFlow Comprehensive Benchmark Suite")
        print("=" * 60)

        # Create test data
        print("\nGenerating test data...")
        test_data = self.create_test_data()

        # Run benchmarks
        all_results = []
        for name, data in test_data.items():
            print(f"\nBenchmarking {name} ({len(data):,} bytes)...")
            results = self.benchmark_compressor(data, name)
            all_results.append(results)
            self.print_results(results)

        # Summary
        self.print_summary(all_results)

        return all_results

    def print_results(self, results: Dict):
        """Print benchmark results for a single test"""
        print(f"\n  Results for {results['data_name']}:")
        print(f"  Original size: {results['original_size']:,} bytes")
        print("-" * 80)
        print(f"  {'Compressor':<20} {'Size':>12} {'Ratio':>8} {'C Speed':>10} {'D Speed':>10}")
        print(f"  {'':20} {'(bytes)':>12} {'':>8} {'(MB/s)':>10} {'(MB/s)':>10}")
        print("-" * 80)

        for name, stats in sorted(results['compressors'].items()):
            print(f"  {name:<20} {stats['compressed_size']:>12,} {stats['ratio']:>7.2f}x "
                  f"{stats['compress_speed_mbps']:>9.1f} {stats['decompress_speed_mbps']:>9.1f}")

    def print_summary(self, all_results: List[Dict]):
        """Print summary of all benchmarks"""
        print("\n" + "=" * 80)
        print("SUMMARY - Average Compression Ratios")
        print("=" * 80)

        compressor_names = list(all_results[0]['compressors'].keys())
        summary = {name: [] for name in compressor_names}

        for result in all_results:
            for name, stats in result['compressors'].items():
                summary[name].append(stats['ratio'])

        print(f"{'Compressor':<25} {'Average Ratio':>15} {'Best Ratio':>15} {'Worst Ratio':>15}")
        print("-" * 70)

        for name in sorted(summary.keys()):
            ratios = summary[name]
            avg_ratio = sum(ratios) / len(ratios)
            best_ratio = max(ratios)
            worst_ratio = min(ratios)
            print(f"{name:<25} {avg_ratio:>14.2f}x {best_ratio:>14.2f}x {worst_ratio:>14.2f}x")

        # Comparison to gzip
        print("\n" + "=" * 80)
        print("COMPARISON TO GZIP (Ratio Improvement)")
        print("=" * 80)

        gzip_ratios = summary['gzip']
        for name in sorted(summary.keys()):
            if name == 'gzip':
                continue
            ratios = summary[name]
            improvements = [(r / g - 1) * 100 for r, g in zip(ratios, gzip_ratios)]
            avg_improvement = sum(improvements) / len(improvements)
            print(f"{name:<25} {avg_improvement:>+6.1f}% average improvement")


def main():
    """Main entry point for benchmarking"""
    suite = BenchmarkSuite()
    results = suite.run_full_benchmark()

    # Save results to JSON
    output_file = Path("benchmark_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to {output_file}")


if __name__ == '__main__':
    main()