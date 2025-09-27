#!/usr/bin/env python3
"""
ContextFlow Simple Demo - Demonstrates the critical bug fix
Shows that the decompress method now works correctly
"""

import sys
import os
sys.path.insert(0, os.path.abspath('..'))

from contextflow.src.advanced_compressor import AdvancedCompressor
from contextflow.src.compressor import ContextFlowCompressor

def test_standard_compression():
    """Test standard ContextFlow compression (CTXF format)"""
    print("\n" + "="*60)
    print("STANDARD CONTEXTFLOW COMPRESSION (CTXF Format)")
    print("="*60)

    compressor = ContextFlowCompressor()
    test_data = b"Hello, World! This is a test of ContextFlow compression." * 50

    print(f"Original size: {len(test_data)} bytes")
    print(f"First 50 bytes: {test_data[:50]}")

    # Compress
    compressed = compressor.compress(test_data)
    print(f"\nCompressed size: {len(compressed)} bytes")
    print(f"Compression ratio: {len(test_data)/len(compressed):.2f}x")
    print(f"Format: {compressed[:4]}")  # Should be b'CTXF'

    # Decompress using AdvancedCompressor (which now delegates to ContextFlowDecompressor)
    advanced = AdvancedCompressor()
    decompressed = advanced.decompress(compressed)

    print(f"\nDecompressed size: {len(decompressed)} bytes")

    # Verify
    if decompressed == test_data:
        print("[SUCCESS] Perfect reconstruction using AdvancedCompressor.decompress()")
        print("The critical bug has been fixed - decompress() now works!")
        return True
    else:
        print("[FAILED] Data mismatch")
        return False

def test_simple_data():
    """Test with various simple data patterns"""
    print("\n" + "="*60)
    print("SIMPLE DATA TESTS")
    print("="*60)

    advanced = AdvancedCompressor()
    test_cases = [
        (b"Simple text", "standard"),
        (b"A" * 100, "standard"),
        (b"12345" * 20, "standard"),
        (b'{"key": "value"}', "standard")
    ]

    results = []
    for data, mode in test_cases:
        print(f"\nTest: {data[:20]}... ({len(data)} bytes, mode: {mode})")

        # Use standard mode which works reliably
        compressed = advanced.compress(data, mode=mode)
        print(f"  Compressed: {len(compressed)} bytes")

        decompressed = advanced.decompress(compressed)
        print(f"  Decompressed: {len(decompressed)} bytes")

        if decompressed == data:
            print("  [PASS] Data matches")
            results.append(True)
        else:
            print("  [FAIL] Data mismatch")
            results.append(False)

    return all(results)

def main():
    print("="*70)
    print("   CONTEXTFLOW DECOMPRESSION BUG FIX VERIFICATION")
    print("="*70)
    print("\nThis demo verifies that the critical decompression bug")
    print("in AdvancedCompressor has been successfully fixed.")
    print("\nBefore fix: decompress() returned compressed data unchanged")
    print("After fix: decompress() properly delegates to ContextFlowDecompressor")

    # Test 1: Standard compression
    test1 = test_standard_compression()

    # Test 2: Simple data patterns
    test2 = test_simple_data()

    # Summary
    print("\n" + "="*70)
    print("                    FINAL SUMMARY")
    print("="*70)

    if test1 and test2:
        print("\nALL TESTS PASSED!")
        print("\nThe critical bug has been successfully fixed:")
        print("- AdvancedCompressor.decompress() now works correctly")
        print("- It properly delegates to ContextFlowDecompressor")
        print("- Standard CTXF format compression/decompression is functional")
        print("\nNote: TurboCompressor and QuantumCompressor have separate")
        print("implementation issues that need addressing in their compress")
        print("methods (they only compress first block), but the main")
        print("decompression pipeline is now fixed.")
    else:
        print("\nSome tests failed. Further investigation needed.")

    return test1 and test2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)