"""
ContextFlow Benchmark Suite
Compare against gzip, zstd, bzip2 on standard corpuses
"""

import time
import os
import sys
import json
import zlib
import bz2
import gzip
from pathlib import Path
from typing import Dict, List, Tuple
import urllib.request
import tarfile
import zipfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextflow.src.production_compressor import compress_production, decompress_production


class BenchmarkSuite:
    """Comprehensive compression benchmark suite"""

    def __init__(self, download_dir: str = "benchmarks/corpuses"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Standard corpus URLs
        self.corpuses = {
            'canterbury': {
                'url': 'https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz',
                'files': ['alice29.txt', 'asyoulik.txt', 'cp.html', 'fields.c',
                         'grammar.lsp', 'kennedy.xls', 'lcet10.txt', 'plrabn12.txt',
                         'ptt5', 'sum', 'xargs.1']
            },
            'calgary': {
                # Calgary corpus files (individual downloads)
                'files': {
                    'bib': 111261,
                    'book1': 768771,
                    'book2': 610856,
                    'geo': 102400,
                    'news': 377109,
                    'obj1': 21504,
                    'obj2': 246814,
                    'paper1': 53161,
                    'paper2': 82199,
                    'pic': 513216,
                    'progc': 39611,
                    'progl': 71646,
                    'progp': 49379,
                    'trans': 93695
                }
            },
            'silesia': {
                # Silesia corpus (subset for testing)
                'files': {
                    'dickens': 10192446,
                    'mozilla': 51220480,
                    'mr': 9970564,
                    'nci': 33553445,
                    'ooffice': 6152192,
                    'osdb': 10085684,
                    'reymont': 6627202,
                    'samba': 21606400,
                    'sao': 7251944,
                    'webster': 41458703,
                    'x-ray': 8474240,
                    'xml': 5345280
                }
            }
        }

    def download_test_files(self):
        """Download sample test files if not present"""
        test_files = []

        # Create sample files for testing
        sample_dir = self.download_dir / "samples"
        sample_dir.mkdir(exist_ok=True)

        # Text file
        text_file = sample_dir / "sample.txt"
        if not text_file.exists():
            text_content = """The quick brown fox jumps over the lazy dog. """ * 1000
            text_content += """Lorem ipsum dolor sit amet, consectetur adipiscing elit. """ * 500
            text_file.write_bytes(text_content.encode('utf-8'))
        test_files.append(text_file)

        # JSON file
        json_file = sample_dir / "sample.json"
        if not json_file.exists():
            json_data = {
                "users": [{"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
                         for i in range(100)],
                "products": [{"id": i, "name": f"Product{i}", "price": i * 10.99}
                           for i in range(200)]
            }
            json_file.write_text(json.dumps(json_data, indent=2))
        test_files.append(json_file)

        # Code file
        code_file = sample_dir / "sample.py"
        if not code_file.exists():
            code_content = '''
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process(self):
        result = []
        for item in self.data:
            if self.validate(item):
                result.append(self.transform(item))
        return result

    def validate(self, item):
        return item is not None

    def transform(self, item):
        return str(item).upper()
''' * 50
            code_file.write_text(code_content)
        test_files.append(code_file)

        # Binary file (random data)
        binary_file = sample_dir / "sample.bin"
        if not binary_file.exists():
            import random
            binary_data = bytes([random.randint(0, 255) for _ in range(100000)])
            binary_file.write_bytes(binary_data)
        test_files.append(binary_file)

        # XML file
        xml_file = sample_dir / "sample.xml"
        if not xml_file.exists():
            xml_content = '''<?xml version="1.0"?>
<catalog>
''' + ''.join([f'''  <book id="{i}">
    <author>Author {i}</author>
    <title>Title {i}</title>
    <genre>Computer</genre>
    <price>{i * 10.99}</price>
    <publish_date>2024-01-{(i % 30) + 1:02d}</publish_date>
    <description>Description for book {i}.</description>
  </book>
''' for i in range(100)]) + '''</catalog>'''
            xml_file.write_text(xml_content)
        test_files.append(xml_file)

        return test_files

    def benchmark_compressor(self, data: bytes, name: str, compress_func, decompress_func) -> Dict:
        """Benchmark a single compressor"""
        # Compression
        start_time = time.perf_counter()
        compressed = compress_func(data)
        compress_time = time.perf_counter() - start_time

        # Decompression
        start_time = time.perf_counter()
        decompressed = decompress_func(compressed)
        decompress_time = time.perf_counter() - start_time

        # Verify correctness
        if decompressed != data:
            print(f"WARNING: {name} decompression mismatch!")
            correct = False
        else:
            correct = True

        return {
            'name': name,
            'compressed_size': len(compressed),
            'ratio': len(data) / len(compressed),
            'compression_bps': len(data) * 8 / len(compressed),
            'compress_time': compress_time,
            'decompress_time': decompress_time,
            'compress_speed_mb': (len(data) / (1024 * 1024)) / compress_time if compress_time > 0 else 0,
            'decompress_speed_mb': (len(data) / (1024 * 1024)) / decompress_time if decompress_time > 0 else 0,
            'correct': correct
        }

    def run_benchmarks(self, test_files: List[Path] = None):
        """Run benchmarks on test files"""
        if test_files is None:
            test_files = self.download_test_files()

        results = []

        for file_path in test_files:
            print(f"\n{'='*60}")
            print(f"Testing: {file_path.name}")
            print(f"Size: {file_path.stat().st_size:,} bytes")
            print(f"{'='*60}")

            data = file_path.read_bytes()

            # Test ContextFlow
            print("Testing ContextFlow...")
            for level in [1, 6, 9]:
                result = self.benchmark_compressor(
                    data,
                    f"ContextFlow-L{level}",
                    lambda d: compress_production(d, level=level),
                    decompress_production
                )
                results.append({'file': file_path.name, **result})
                self._print_result(result)

            # Test gzip
            print("\nTesting gzip...")
            for level in [1, 6, 9]:
                result = self.benchmark_compressor(
                    data,
                    f"gzip-L{level}",
                    lambda d, l=level: gzip.compress(d, compresslevel=l),
                    gzip.decompress
                )
                results.append({'file': file_path.name, **result})
                self._print_result(result)

            # Test bzip2
            print("\nTesting bzip2...")
            for level in [1, 5, 9]:
                result = self.benchmark_compressor(
                    data,
                    f"bzip2-L{level}",
                    lambda d, l=level: bz2.compress(d, compresslevel=l),
                    bz2.decompress
                )
                results.append({'file': file_path.name, **result})
                self._print_result(result)

            # Test zlib
            print("\nTesting zlib...")
            for level in [1, 6, 9]:
                result = self.benchmark_compressor(
                    data,
                    f"zlib-L{level}",
                    lambda d, l=level: zlib.compress(d, level=l),
                    zlib.decompress
                )
                results.append({'file': file_path.name, **result})
                self._print_result(result)

        return results

    def _print_result(self, result: Dict):
        """Print benchmark result"""
        print(f"  {result['name']:20} "
              f"Ratio: {result['ratio']:.2f}x  "
              f"BPS: {result['compression_bps']:.2f}  "
              f"Compress: {result['compress_speed_mb']:.1f} MB/s  "
              f"Decompress: {result['decompress_speed_mb']:.1f} MB/s")

    def print_summary(self, results: List[Dict]):
        """Print summary of all results"""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")

        # Group by file
        files = {}
        for result in results:
            file_name = result['file']
            if file_name not in files:
                files[file_name] = []
            files[file_name].append(result)

        for file_name, file_results in files.items():
            print(f"\n{file_name}:")
            print(f"{'Compressor':20} {'Ratio':>8} {'BPS':>8} {'C Speed':>12} {'D Speed':>12}")
            print("-" * 70)

            # Sort by compression ratio
            sorted_results = sorted(file_results, key=lambda x: x['ratio'], reverse=True)

            for result in sorted_results:
                print(f"{result['name']:20} "
                      f"{result['ratio']:8.2f}x "
                      f"{result['compression_bps']:8.2f} "
                      f"{result['compress_speed_mb']:10.1f} MB/s "
                      f"{result['decompress_speed_mb']:10.1f} MB/s")

        # Overall winners
        print(f"\n{'='*80}")
        print("OVERALL PERFORMANCE")
        print(f"{'='*80}")

        # Best compression ratio
        best_ratio = max(results, key=lambda x: x['ratio'])
        print(f"Best Compression Ratio: {best_ratio['name']} ({best_ratio['ratio']:.2f}x)")

        # Fastest compression
        best_compress = max(results, key=lambda x: x['compress_speed_mb'])
        print(f"Fastest Compression: {best_compress['name']} ({best_compress['compress_speed_mb']:.1f} MB/s)")

        # Fastest decompression
        best_decompress = max(results, key=lambda x: x['decompress_speed_mb'])
        print(f"Fastest Decompression: {best_decompress['name']} ({best_decompress['decompress_speed_mb']:.1f} MB/s)")

        # Best balanced (ratio * sqrt(compress_speed * decompress_speed))
        def balance_score(r):
            return r['ratio'] * ((r['compress_speed_mb'] * r['decompress_speed_mb']) ** 0.5)

        best_balanced = max(results, key=balance_score)
        print(f"Best Balanced: {best_balanced['name']} "
              f"(Ratio: {best_balanced['ratio']:.2f}x, "
              f"Speed: {best_balanced['compress_speed_mb']:.1f}/{best_balanced['decompress_speed_mb']:.1f} MB/s)")


def main():
    """Run benchmark suite"""
    print("ContextFlow Compression Benchmark Suite")
    print("=" * 80)

    benchmark = BenchmarkSuite()

    # Run benchmarks
    results = benchmark.run_benchmarks()

    # Print summary
    benchmark.print_summary(results)

    # Save results
    output_file = Path("benchmarks/results.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()