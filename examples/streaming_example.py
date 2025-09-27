#!/usr/bin/env python3
"""
Streaming compression example for ContextFlow
Shows how to compress large files in chunks
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextflow import ContextFlowCompressor, ContextFlowDecompressor
import io


def compress_stream(input_stream, output_stream, chunk_size=65536):
    """
    Compress data from input stream to output stream in chunks

    Args:
        input_stream: Input file-like object
        output_stream: Output file-like object
        chunk_size: Size of chunks to process
    """
    compressor = ContextFlowCompressor(mode='balanced')

    # Process in chunks
    while True:
        chunk = input_stream.read(chunk_size)
        if not chunk:
            break

        # Compress chunk
        compressed = compressor.compress(chunk)

        # Write compressed size and data
        output_stream.write(len(compressed).to_bytes(4, 'little'))
        output_stream.write(compressed)

    print(f"Compressed {input_stream.tell()} bytes")


def decompress_stream(input_stream, output_stream):
    """
    Decompress data from input stream to output stream

    Args:
        input_stream: Input file-like object with compressed data
        output_stream: Output file-like object
    """
    decompressor = ContextFlowDecompressor()

    # Process compressed chunks
    while True:
        # Read chunk size
        size_bytes = input_stream.read(4)
        if not size_bytes:
            break

        chunk_size = int.from_bytes(size_bytes, 'little')

        # Read and decompress chunk
        compressed_chunk = input_stream.read(chunk_size)
        decompressed = decompressor.decompress(compressed_chunk)

        # Write decompressed data
        output_stream.write(decompressed)

    print(f"Decompressed to {output_stream.tell()} bytes")


def example_stream_compression():
    """Example of streaming compression"""
    print("Streaming Compression Example")
    print("-" * 40)

    # Create sample data
    sample_data = b"This is sample data for streaming. " * 1000

    # Compress using streams
    input_stream = io.BytesIO(sample_data)
    compressed_stream = io.BytesIO()

    print("Compressing...")
    compress_stream(input_stream, compressed_stream)

    # Decompress using streams
    compressed_stream.seek(0)
    output_stream = io.BytesIO()

    print("Decompressing...")
    decompress_stream(compressed_stream, output_stream)

    # Verify
    output_stream.seek(0)
    decompressed_data = output_stream.read()

    if decompressed_data == sample_data:
        print("[OK] Streaming compression verified")
        print(f"Original:    {len(sample_data)} bytes")
        print(f"Compressed:  {compressed_stream.tell()} bytes")
        print(f"Ratio:       {len(sample_data)/compressed_stream.tell():.2f}x")
    else:
        print("[ERROR] Data mismatch!")


def example_file_streaming():
    """Example of compressing large files with streaming"""
    print("\nLarge File Streaming Example")
    print("-" * 40)

    # Create a large sample file
    large_file = Path("large_sample.txt")
    print("Creating large sample file...")
    with open(large_file, 'wb') as f:
        for i in range(1000):
            f.write(f"Line {i}: This is sample data that will be compressed using streaming.\n".encode())

    original_size = large_file.stat().st_size
    print(f"Original file size: {original_size:,} bytes")

    # Compress the file
    compressed_file = Path("large_sample.ctxf")
    print("Compressing file...")
    with open(large_file, 'rb') as input_f:
        with open(compressed_file, 'wb') as output_f:
            compress_stream(input_f, output_f, chunk_size=8192)

    compressed_size = compressed_file.stat().st_size
    print(f"Compressed file size: {compressed_size:,} bytes")
    print(f"Compression ratio: {original_size/compressed_size:.2f}x")

    # Decompress the file
    decompressed_file = Path("large_sample_restored.txt")
    print("Decompressing file...")
    with open(compressed_file, 'rb') as input_f:
        with open(decompressed_file, 'wb') as output_f:
            decompress_stream(input_f, output_f)

    # Verify
    with open(large_file, 'rb') as f1:
        with open(decompressed_file, 'rb') as f2:
            if f1.read() == f2.read():
                print("[OK] File streaming verified")
            else:
                print("[ERROR] File content mismatch!")

    # Clean up
    large_file.unlink()
    compressed_file.unlink()
    decompressed_file.unlink()


if __name__ == "__main__":
    print("=" * 50)
    print("     ContextFlow Streaming Examples")
    print("=" * 50)
    print()

    example_stream_compression()
    example_file_streaming()

    print("\n" + "=" * 50)
    print("     Streaming examples completed!")
    print("=" * 50)