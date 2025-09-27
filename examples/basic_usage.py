#!/usr/bin/env python3
"""
Basic usage examples for ContextFlow compression
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import contextflow

def example_simple_compression():
    """Simple compression and decompression example"""
    print("Example 1: Simple Compression")
    print("-" * 40)

    # Your data to compress
    original_data = b"Hello, World! This is ContextFlow compression." * 10

    # Compress the data
    compressed = contextflow.compress(original_data)

    # Decompress the data
    decompressed = contextflow.decompress(compressed)

    # Verify
    assert decompressed == original_data, "Decompression failed!"

    print(f"Original size:    {len(original_data)} bytes")
    print(f"Compressed size:  {len(compressed)} bytes")
    print(f"Compression ratio: {len(original_data)/len(compressed):.2f}x")
    print("[OK] Data verified successfully\n")


def example_compression_modes():
    """Example showing different compression modes"""
    print("Example 2: Compression Modes")
    print("-" * 40)

    data = b"Sample data for compression testing." * 50

    # Fast mode - prioritize speed
    compressed_fast = contextflow.compress(data, mode='fast', fast_mode=True)
    print(f"Fast mode:     {len(compressed_fast)} bytes")

    # Balanced mode - balance between speed and ratio (default)
    compressed_balanced = contextflow.compress(data, mode='balanced')
    print(f"Balanced mode: {len(compressed_balanced)} bytes")

    # Maximum compression - best ratio
    compressed_max = contextflow.compress(data, mode='max_compression')
    print(f"Max mode:      {len(compressed_max)} bytes")

    print(f"Original:      {len(data)} bytes\n")


def example_file_compression():
    """Example of compressing files"""
    print("Example 3: File Compression")
    print("-" * 40)

    # Create a sample file
    sample_file = Path("sample.txt")
    sample_file.write_text("This is a sample file for compression.\n" * 100)

    # Compress the file
    with open(sample_file, 'rb') as f:
        file_data = f.read()

    compressed = contextflow.compress(file_data)

    # Save compressed file
    compressed_file = Path("sample.ctxf")
    compressed_file.write_bytes(compressed)

    print(f"Original file:    {sample_file.stat().st_size} bytes")
    print(f"Compressed file:  {compressed_file.stat().st_size} bytes")
    print(f"Compression ratio: {sample_file.stat().st_size/compressed_file.stat().st_size:.2f}x")

    # Clean up
    sample_file.unlink()
    compressed_file.unlink()
    print("[OK] File compression successful\n")


def example_json_compression():
    """Example of compressing JSON data"""
    print("Example 4: JSON Compression")
    print("-" * 40)

    import json

    # Create JSON data
    data = {
        "users": [
            {"id": i, "name": f"User_{i}", "email": f"user{i}@example.com"}
            for i in range(100)
        ],
        "metadata": {
            "version": "1.0",
            "created": "2024-01-01"
        }
    }

    # Convert to bytes
    json_bytes = json.dumps(data, indent=2).encode('utf-8')

    # Compress
    compressed = contextflow.compress(json_bytes)

    # Decompress and verify
    decompressed = contextflow.decompress(compressed)
    recovered_data = json.loads(decompressed.decode('utf-8'))

    print(f"Original JSON:    {len(json_bytes)} bytes")
    print(f"Compressed:       {len(compressed)} bytes")
    print(f"Compression ratio: {len(json_bytes)/len(compressed):.2f}x")
    print(f"Records preserved: {len(recovered_data['users'])} users")
    print("[OK] JSON compression successful\n")


def example_advanced_usage():
    """Advanced usage with direct compressor access"""
    print("Example 5: Advanced Usage")
    print("-" * 40)

    from contextflow import ContextFlowCompressor, ContextFlowDecompressor

    # Create compressor with custom settings
    compressor = ContextFlowCompressor(mode='balanced', fast_mode=False)

    # Compress data
    data = b"Advanced compression example with direct API access." * 20
    compressed = compressor.compress(data)

    # Create decompressor
    decompressor = ContextFlowDecompressor()
    decompressed = decompressor.decompress(compressed)

    # Verify
    assert decompressed == data

    print(f"Original:    {len(data)} bytes")
    print(f"Compressed:  {len(compressed)} bytes")
    print(f"Ratio:       {len(data)/len(compressed):.2f}x")
    print("[OK] Advanced usage successful\n")


if __name__ == "__main__":
    print("=" * 50)
    print("     ContextFlow Usage Examples")
    print("=" * 50)
    print()

    example_simple_compression()
    example_compression_modes()
    example_file_compression()
    example_json_compression()
    example_advanced_usage()

    print("=" * 50)
    print("     All examples completed successfully!")
    print("=" * 50)