#!/usr/bin/env python3
"""
ContextFlow CLI - Command line interface for ContextFlow compression
"""

import argparse
import sys
import os
import time
from pathlib import Path
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextflow import compress, decompress, __version__


class CLI:
    """Command line interface for ContextFlow"""

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            prog='contextflow',
            description='ContextFlow - Advanced hybrid lossless compression',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  contextflow compress input.txt                 # Compress with default settings
  contextflow compress -o output.ctxf input.txt  # Specify output file
  contextflow compress -m fast input.txt         # Fast compression
  contextflow compress -m max input.txt          # Maximum compression
  contextflow decompress compressed.ctxf         # Decompress file
  contextflow benchmark input.txt                # Run benchmark

Compression modes:
  balanced - Balance between speed and compression (default)
  fast     - Prioritize speed over compression
  max      - Maximum compression ratio
            """
        )

        parser.add_argument('--version', action='version', version=f'ContextFlow {__version__}')

        subparsers = parser.add_subparsers(dest='command', help='Commands')

        compress_parser = subparsers.add_parser('compress', help='Compress files')
        compress_parser.add_argument('input', help='Input file to compress')
        compress_parser.add_argument('-o', '--output', help='Output file (default: input.ctxf)')
        compress_parser.add_argument('-m', '--mode', choices=['balanced', 'fast', 'max'],
                                    default='balanced', help='Compression mode')
        compress_parser.add_argument('--fast', action='store_true', help='Enable fast mode (skip neural mixing)')
        compress_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

        decompress_parser = subparsers.add_parser('decompress', help='Decompress files')
        decompress_parser.add_argument('input', help='Compressed file to decompress')
        decompress_parser.add_argument('-o', '--output', help='Output file')
        decompress_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

        benchmark_parser = subparsers.add_parser('benchmark', help='Run compression benchmark')
        benchmark_parser.add_argument('input', help='Input file to benchmark')
        benchmark_parser.add_argument('--compare', nargs='+', choices=['gzip', 'bzip2', 'zstd', 'lzma'],
                                     help='Compare with other compressors')
        benchmark_parser.add_argument('--iterations', type=int, default=3, help='Number of iterations')

        info_parser = subparsers.add_parser('info', help='Show compressed file information')
        info_parser.add_argument('input', help='Compressed file to analyze')

        return parser

    def run(self, args: Optional[list] = None) -> int:
        """Run CLI with given arguments"""
        args = self.parser.parse_args(args)

        if not args.command:
            self.parser.print_help()
            return 0

        try:
            if args.command == 'compress':
                return self._compress(args)
            elif args.command == 'decompress':
                return self._decompress(args)
            elif args.command == 'benchmark':
                return self._benchmark(args)
            elif args.command == 'info':
                return self._info(args)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        return 0

    def _compress(self, args) -> int:
        """Handle compression command"""
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
            return 1

        output_path = Path(args.output) if args.output else input_path.with_suffix('.ctxf')

        if output_path.exists() and not self._confirm_overwrite(output_path):
            return 1

        if args.verbose:
            print(f"Compressing {input_path}")
            print(f"Mode: {args.mode}")
            print(f"Fast mode: {args.fast}")

        start_time = time.time()
        original_size = input_path.stat().st_size

        with open(input_path, 'rb') as f:
            data = f.read()

        compressed = compress(data, mode=args.mode, fast_mode=args.fast)

        with open(output_path, 'wb') as f:
            f.write(compressed)

        elapsed_time = time.time() - start_time
        compressed_size = len(compressed)
        ratio = original_size / compressed_size if compressed_size > 0 else 0
        speed = original_size / (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0

        print(f"Compressed {input_path.name} -> {output_path.name}")
        print(f"Original size: {self._format_size(original_size)}")
        print(f"Compressed size: {self._format_size(compressed_size)}")
        print(f"Compression ratio: {ratio:.2f}x")
        print(f"Time: {elapsed_time:.2f}s ({speed:.1f} MB/s)")

        return 0

    def _decompress(self, args) -> int:
        """Handle decompression command"""
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
            return 1

        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix('')
            if output_path == input_path:
                output_path = input_path.with_suffix('.decompressed')

        if output_path.exists() and not self._confirm_overwrite(output_path):
            return 1

        if args.verbose:
            print(f"Decompressing {input_path}")

        start_time = time.time()

        with open(input_path, 'rb') as f:
            compressed = f.read()

        decompressed = decompress(compressed)

        with open(output_path, 'wb') as f:
            f.write(decompressed)

        elapsed_time = time.time() - start_time
        speed = len(decompressed) / (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0

        print(f"Decompressed {input_path.name} -> {output_path.name}")
        print(f"Size: {self._format_size(len(decompressed))}")
        print(f"Time: {elapsed_time:.2f}s ({speed:.1f} MB/s)")

        return 0

    def _benchmark(self, args) -> int:
        """Handle benchmark command"""
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
            return 1

        with open(input_path, 'rb') as f:
            data = f.read()

        original_size = len(data)
        print(f"Benchmarking {input_path.name}")
        print(f"File size: {self._format_size(original_size)}\n")

        results = []

        for mode in ['fast', 'balanced', 'max']:
            print(f"Testing ContextFlow ({mode} mode)...")

            compress_times = []
            decompress_times = []
            compressed_size = 0

            for i in range(args.iterations):
                start = time.time()
                compressed = compress(data, mode=mode, fast_mode=(mode == 'fast'))
                compress_times.append(time.time() - start)
                compressed_size = len(compressed)

                start = time.time()
                decompressed = decompress(compressed)
                decompress_times.append(time.time() - start)

                assert decompressed == data, "Decompression verification failed"

            avg_compress = sum(compress_times) / len(compress_times)
            avg_decompress = sum(decompress_times) / len(decompress_times)
            ratio = original_size / compressed_size

            results.append({
                'name': f'ContextFlow ({mode})',
                'compressed_size': compressed_size,
                'ratio': ratio,
                'compress_time': avg_compress,
                'decompress_time': avg_decompress,
                'compress_speed': original_size / (1024 * 1024 * avg_compress),
                'decompress_speed': original_size / (1024 * 1024 * avg_decompress)
            })

        if args.compare:
            for compressor in args.compare:
                result = self._benchmark_external(data, compressor, args.iterations)
                if result:
                    results.append(result)

        print("\nResults:")
        print("-" * 80)
        print(f"{'Compressor':<20} {'Size':<12} {'Ratio':<8} {'Compress':<12} {'Decompress':<12}")
        print(f"{'':20} {'':12} {'':8} {'MB/s':<12} {'MB/s':<12}")
        print("-" * 80)

        for r in results:
            print(f"{r['name']:<20} {self._format_size(r['compressed_size']):<12} "
                  f"{r['ratio']:.2f}x     {r['compress_speed']:.1f} MB/s     "
                  f"{r['decompress_speed']:.1f} MB/s")

        return 0

    def _benchmark_external(self, data: bytes, compressor: str, iterations: int) -> Optional[dict]:
        """Benchmark external compressor"""
        print(f"Testing {compressor}...")

        try:
            if compressor == 'gzip':
                import gzip
                compress_func = lambda d: gzip.compress(d, compresslevel=9)
                decompress_func = gzip.decompress
            elif compressor == 'bzip2':
                import bz2
                compress_func = lambda d: bz2.compress(d, compresslevel=9)
                decompress_func = bz2.decompress
            elif compressor == 'lzma':
                import lzma
                compress_func = lambda d: lzma.compress(d, preset=9)
                decompress_func = lzma.decompress
            elif compressor == 'zstd':
                try:
                    import zstandard as zstd
                    cctx = zstd.ZstdCompressor(level=19)
                    dctx = zstd.ZstdDecompressor()
                    compress_func = cctx.compress
                    decompress_func = dctx.decompress
                except ImportError:
                    print(f"  Warning: zstd not installed, skipping")
                    return None
            else:
                return None

            compress_times = []
            decompress_times = []
            compressed_size = 0

            for _ in range(iterations):
                start = time.time()
                compressed = compress_func(data)
                compress_times.append(time.time() - start)
                compressed_size = len(compressed)

                start = time.time()
                decompressed = decompress_func(compressed)
                decompress_times.append(time.time() - start)

            avg_compress = sum(compress_times) / len(compress_times)
            avg_decompress = sum(decompress_times) / len(decompress_times)

            return {
                'name': compressor,
                'compressed_size': compressed_size,
                'ratio': len(data) / compressed_size,
                'compress_time': avg_compress,
                'decompress_time': avg_decompress,
                'compress_speed': len(data) / (1024 * 1024 * avg_compress),
                'decompress_speed': len(data) / (1024 * 1024 * avg_decompress)
            }

        except Exception as e:
            print(f"  Error testing {compressor}: {e}")
            return None

    def _info(self, args) -> int:
        """Show compressed file information"""
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
            return 1

        with open(input_path, 'rb') as f:
            data = f.read()

        if len(data) < 16 or data[:4] != b'CTXF':
            print("Error: Not a valid ContextFlow file", file=sys.stderr)
            return 1

        version = data[4]
        flags = data[5]
        block_size = struct.unpack('<H', data[6:8])[0] << 10
        compressed_size = struct.unpack('<I', data[8:12])[0]

        meta_size = struct.unpack('<I', data[12:16])[0]
        import json
        try:
            metadata = json.loads(data[16:16 + meta_size].decode('utf-8'))
        except:
            metadata = {}

        print(f"ContextFlow Archive Information")
        print("-" * 40)
        print(f"Version: {version}")
        print(f"Block size: {self._format_size(block_size)}")
        print(f"Fast mode: {bool(flags & 0x01)}")
        print(f"Max compression: {bool(flags & 0x02)}")
        print(f"Data type: {metadata.get('data_type', 'unknown')}")
        print(f"Original size: {self._format_size(metadata.get('original_size', 0))}")
        print(f"Compressed size: {self._format_size(len(data))}")
        print(f"Compression ratio: {metadata.get('compression_ratio', 0):.2f}x")
        print(f"Blocks: {len(metadata.get('blocks', []))}")

        return 0

    def _confirm_overwrite(self, path: Path) -> bool:
        """Confirm file overwrite"""
        response = input(f"File '{path}' exists. Overwrite? (y/n): ")
        return response.lower() == 'y'

    def _format_size(self, size: int) -> str:
        """Format size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


def main():
    """Main entry point"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()