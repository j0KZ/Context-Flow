#!/usr/bin/env python3
"""
ContextFlow Interactive Demo
Try out the compression system with your own files!
"""

import os
import sys
import time

# Add contextflow to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'contextflow'))

from src.turbo_compressor import TurboCompressor
from src.quantum_compressor import QuantumCompressor
from src.advanced_compressor import AdvancedCompressor
from src.config import FeatureFlags, CompressionConfig

def format_bytes(bytes):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def compress_file(input_file, output_file=None, compressor_type='turbo'):
    """Compress a file"""
    print(f"\n{'='*60}")
    print(f"Compressing: {input_file}")
    print(f"Using: {compressor_type.upper()} Compressor")
    print('='*60)

    # Select compressor
    if compressor_type == 'quantum':
        compressor = QuantumCompressor()
    elif compressor_type == 'advanced':
        compressor = AdvancedCompressor()
    else:
        compressor = TurboCompressor()

    # Read input file
    try:
        with open(input_file, 'rb') as f:
            data = f.read()
        original_size = len(data)
        print(f"Original size: {format_bytes(original_size)}")

        # Compress
        print("Compressing...")
        start = time.time()
        compressed = compressor.compress(data)
        compress_time = time.time() - start
        compressed_size = len(compressed)

        # Calculate ratio
        ratio = original_size / compressed_size if compressed_size > 0 else 0

        # Save compressed file
        if output_file is None:
            output_file = input_file + '.ctx'

        with open(output_file, 'wb') as f:
            f.write(compressed)

        print(f"\n✓ Compression complete!")
        print(f"  Compressed size: {format_bytes(compressed_size)}")
        print(f"  Compression ratio: {ratio:.2f}x")
        print(f"  Time: {compress_time:.2f}s")
        print(f"  Saved to: {output_file}")

        return output_file

    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def decompress_file(input_file, output_file=None, compressor_type='turbo'):
    """Decompress a file"""
    print(f"\n{'='*60}")
    print(f"Decompressing: {input_file}")
    print(f"Using: {compressor_type.upper()} Compressor")
    print('='*60)

    # Select compressor
    if compressor_type == 'quantum':
        compressor = QuantumCompressor()
    elif compressor_type == 'advanced':
        compressor = AdvancedCompressor()
    else:
        compressor = TurboCompressor()

    try:
        # Read compressed file
        with open(input_file, 'rb') as f:
            compressed = f.read()
        compressed_size = len(compressed)
        print(f"Compressed size: {format_bytes(compressed_size)}")

        # Decompress
        print("Decompressing...")
        start = time.time()
        decompressed = compressor.decompress(compressed)
        decompress_time = time.time() - start
        decompressed_size = len(decompressed)

        # Save decompressed file
        if output_file is None:
            if input_file.endswith('.ctx'):
                output_file = input_file[:-4] + '.decompressed'
            else:
                output_file = input_file + '.decompressed'

        with open(output_file, 'wb') as f:
            f.write(decompressed)

        print(f"\n✓ Decompression complete!")
        print(f"  Decompressed size: {format_bytes(decompressed_size)}")
        print(f"  Time: {decompress_time:.2f}s")
        print(f"  Saved to: {output_file}")

        return output_file

    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_compression(data_or_file=None):
    """Test compression with data or file"""
    if data_or_file is None:
        # Use default test data
        test_data = b"Hello ContextFlow! This is a test of the compression system. " * 100
        print("\nUsing default test data (6.2 KB of repeated text)")
    elif isinstance(data_or_file, bytes):
        test_data = data_or_file
        print(f"\nUsing provided data ({format_bytes(len(test_data))})")
    elif isinstance(data_or_file, str) and os.path.exists(data_or_file):
        with open(data_or_file, 'rb') as f:
            test_data = f.read()
        print(f"\nTesting with file: {data_or_file} ({format_bytes(len(test_data))})")
    else:
        test_data = data_or_file.encode() if isinstance(data_or_file, str) else bytes(data_or_file)
        print(f"\nUsing provided text ({format_bytes(len(test_data))})")

    print("\n" + "="*60)
    print(" COMPRESSION COMPARISON TEST")
    print("="*60)

    compressors = [
        ("Turbo", TurboCompressor()),
        ("Quantum", QuantumCompressor()),
        ("Advanced", AdvancedCompressor())
    ]

    results = []
    for name, compressor in compressors:
        try:
            # Compress
            start = time.time()
            compressed = compressor.compress(test_data)
            compress_time = time.time() - start

            # Decompress
            start = time.time()
            decompressed = compressor.decompress(compressed)
            decompress_time = time.time() - start

            # Verify
            success = decompressed == test_data
            ratio = len(test_data) / len(compressed) if len(compressed) > 0 else 0

            results.append({
                'name': name,
                'compressed_size': len(compressed),
                'ratio': ratio,
                'compress_time': compress_time,
                'decompress_time': decompress_time,
                'success': success
            })

            print(f"\n{name} Compressor:")
            print(f"  Compressed: {format_bytes(len(compressed))}")
            print(f"  Ratio: {ratio:.2f}x")
            print(f"  Compress: {compress_time:.3f}s")
            print(f"  Decompress: {decompress_time:.3f}s")
            print(f"  Status: {'✓ Success' if success else '✗ Failed'}")

        except Exception as e:
            print(f"\n{name} Compressor: ✗ Error - {str(e)[:50]}")

    # Find best compressor
    if results:
        best = max(results, key=lambda x: x['ratio'] if x['success'] else 0)
        print(f"\n{'='*60}")
        print(f" BEST COMPRESSOR: {best['name']} ({best['ratio']:.2f}x compression)")
        print('='*60)

def interactive_demo():
    """Interactive demo menu"""
    print("""
╔══════════════════════════════════════════════════════════╗
║           CONTEXTFLOW COMPRESSION SYSTEM DEMO            ║
╠══════════════════════════════════════════════════════════╣
║  Advanced compression with 3 powerful algorithms:        ║
║  • Turbo: Fast parallel processing                       ║
║  • Quantum: Neural-enhanced compression                  ║
║  • Advanced: Smart multi-algorithm selection             ║
╚══════════════════════════════════════════════════════════╝
""")

    while True:
        print("\nWhat would you like to do?")
        print("1. Compress a file")
        print("2. Decompress a file")
        print("3. Test with sample data")
        print("4. Test with custom text")
        print("5. Compare all compressors")
        print("6. Exit")

        choice = input("\nChoice (1-6): ").strip()

        if choice == '1':
            file = input("Enter file path to compress: ").strip()
            if os.path.exists(file):
                print("\nSelect compressor:")
                print("1. Turbo (fastest)")
                print("2. Quantum (best ratio)")
                print("3. Advanced (smart)")
                comp = input("Choice (1-3): ").strip()
                comp_type = ['turbo', 'quantum', 'advanced'][int(comp)-1] if comp in '123' else 'turbo'
                compress_file(file, compressor_type=comp_type)
            else:
                print("File not found!")

        elif choice == '2':
            file = input("Enter compressed file path: ").strip()
            if os.path.exists(file):
                print("\nSelect decompressor:")
                print("1. Turbo")
                print("2. Quantum")
                print("3. Advanced")
                comp = input("Choice (1-3): ").strip()
                comp_type = ['turbo', 'quantum', 'advanced'][int(comp)-1] if comp in '123' else 'turbo'
                decompress_file(file, compressor_type=comp_type)
            else:
                print("File not found!")

        elif choice == '3':
            test_compression()

        elif choice == '4':
            text = input("Enter text to compress: ")
            test_compression(text)

        elif choice == '5':
            file = input("Enter file to test (or press Enter for default): ").strip()
            if file and os.path.exists(file):
                test_compression(file)
            else:
                test_compression()

        elif choice == '6':
            print("\nThank you for trying ContextFlow!")
            break
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'compress' and len(sys.argv) > 2:
            compress_file(sys.argv[2])
        elif sys.argv[1] == 'decompress' and len(sys.argv) > 2:
            decompress_file(sys.argv[2])
        elif sys.argv[1] == 'test':
            if len(sys.argv) > 2:
                test_compression(sys.argv[2])
            else:
                test_compression()
        else:
            print("Usage:")
            print("  python demo.py                    # Interactive mode")
            print("  python demo.py compress <file>    # Compress a file")
            print("  python demo.py decompress <file>  # Decompress a file")
            print("  python demo.py test [file]        # Test compression")
    else:
        interactive_demo()