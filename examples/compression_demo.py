#!/usr/bin/env python3
"""
ContextFlow Compression Demo - Working Example
Demonstrates all compression modes working correctly after bug fix
"""

import sys
import os
sys.path.insert(0, os.path.abspath('..'))

from contextflow.src.advanced_compressor import AdvancedCompressor
import time

def format_bytes(size):
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def test_compression(compressor, data, mode="turbo", description="Test"):
    """Test compression and decompression for a specific mode"""
    print(f"\n{'='*60}")
    print(f"{description} - Mode: {mode}")
    print(f"{'='*60}")

    print(f"Original size: {format_bytes(len(data))}")
    print(f"First 50 bytes: {data[:50]}...")

    # Compress
    start = time.time()
    compressed = compressor.compress(data, mode=mode)
    compress_time = time.time() - start

    print(f"\nCompressed size: {format_bytes(len(compressed))}")
    print(f"Compression ratio: {len(data)/len(compressed):.2f}x")
    print(f"Compression time: {compress_time:.3f}s")
    print(f"Speed: {format_bytes(len(data)/compress_time)}/s")

    # Decompress
    start = time.time()
    decompressed = compressor.decompress(compressed)
    decompress_time = time.time() - start

    print(f"\nDecompressed size: {format_bytes(len(decompressed))}")
    print(f"Decompression time: {decompress_time:.3f}s")
    print(f"Speed: {format_bytes(len(decompressed)/decompress_time)}/s")

    # Verify
    if decompressed == data:
        print("\n[SUCCESS] Data integrity verified - perfect reconstruction!")
        return True
    else:
        print(f"\n[FAILED] Data mismatch!")
        print(f"Expected size: {len(data)}, Got: {len(decompressed)}")
        return False

def main():
    print("=" * 70)
    print("       CONTEXTFLOW COMPRESSION SYSTEM - WORKING DEMO")
    print("=" * 70)
    print("\nThis demo shows all compression modes working correctly")
    print("after fixing the critical decompression bug.\n")

    compressor = AdvancedCompressor()

    # Test different data types
    test_cases = [
        {
            "data": b"Hello, World! " * 100,
            "mode": "turbo",
            "description": "Simple Text (TurboCompressor)"
        },
        {
            "data": b"The quick brown fox jumps over the lazy dog. " * 500,
            "mode": "quantum",
            "description": "Repetitive Text (QuantumCompressor)"
        },
        {
            "data": bytes(range(256)) * 20,
            "mode": "standard",
            "description": "Binary Data (Standard Mode)"
        },
        {
            "data": b"AAAAAAAAAA" * 1000 + b"BBBBBBBBBB" * 1000,
            "mode": "turbo",
            "description": "Highly Repetitive (TurboCompressor)"
        },
        {
            "data": b'{"name": "test", "value": 123}' * 100,
            "mode": "quantum",
            "description": "JSON Data (QuantumCompressor)"
        },
        {
            "data": b"Small data",
            "mode": "turbo",
            "description": "Small Data (Edge Case)"
        },
        {
            "data": b"X" * 100000,
            "mode": "turbo",
            "description": "Large Uniform Data (100KB)"
        }
    ]

    # Track results
    results = []
    passed = 0
    failed = 0

    for test_case in test_cases:
        success = test_compression(
            compressor,
            test_case["data"],
            test_case["mode"],
            test_case["description"]
        )
        results.append({
            "description": test_case["description"],
            "mode": test_case["mode"],
            "success": success
        })
        if success:
            passed += 1
        else:
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("                        TEST SUMMARY")
    print("=" * 70)
    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(results))*100:.1f}%")

    print("\nDetailed Results:")
    print("-" * 70)
    for result in results:
        status = "[PASS]" if result["success"] else "[FAIL]"
        print(f"{status} {result['description']} ({result['mode']})")

    if failed == 0:
        print("\n" + "=" * 70)
        print("    ALL TESTS PASSED! COMPRESSION SYSTEM FULLY FUNCTIONAL")
        print("=" * 70)
        print("\nThe critical decompression bug has been successfully fixed.")
        print("All compression modes (turbo, quantum, standard) are working correctly.")
    else:
        print("\n" + "=" * 70)
        print(f"    WARNING: {failed} TEST(S) FAILED")
        print("=" * 70)

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)