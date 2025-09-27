#!/usr/bin/env python3
"""
ContextFlow Basic Demo - Shows the critical bug fix working
Demonstrates that AdvancedCompressor.decompress() now correctly
delegates to ContextFlowDecompressor
"""

import sys
import os
sys.path.insert(0, os.path.abspath('..'))

from contextflow.src.compressor import ContextFlowCompressor
from contextflow.src.decompressor import ContextFlowDecompressor
from contextflow.src.advanced_compressor import AdvancedCompressor

def main():
    print("="*70)
    print("     CRITICAL BUG FIX VERIFICATION - DECOMPRESSION WORKING")
    print("="*70)

    print("\nDemonstrating the fix for the critical decompression bug.")
    print("Before: AdvancedCompressor.decompress() returned data unchanged")
    print("After: AdvancedCompressor.decompress() delegates to ContextFlowDecompressor")

    # Test 1: Use ContextFlowCompressor directly (CTXF format)
    print("\n" + "-"*70)
    print("TEST 1: Direct ContextFlow Compression (CTXF format)")
    print("-"*70)

    basic_compressor = ContextFlowCompressor()
    test_data = b"Hello, World! This is a test of the decompression fix." * 10

    print(f"Original size: {len(test_data)} bytes")
    compressed = basic_compressor.compress(test_data)
    print(f"Compressed size: {len(compressed)} bytes")
    print(f"Format detected: {compressed[:4]}")

    # Now decompress using AdvancedCompressor (testing the fix)
    advanced = AdvancedCompressor()
    decompressed_by_advanced = advanced.decompress(compressed)

    # Also decompress directly for comparison
    basic_decompressor = ContextFlowDecompressor()
    decompressed_directly = basic_decompressor.decompress(compressed)

    print(f"\nDecompressed by AdvancedCompressor: {len(decompressed_by_advanced)} bytes")
    print(f"Decompressed directly: {len(decompressed_directly)} bytes")

    if decompressed_by_advanced == test_data:
        print("[SUCCESS] AdvancedCompressor correctly decompressed the data!")
        test1_pass = True
    else:
        print("[FAILED] AdvancedCompressor decompression failed")
        test1_pass = False

    if decompressed_directly == test_data:
        print("[SUCCESS] Direct decompression also works")
    else:
        print("[FAILED] Direct decompression failed")

    # Test 2: Small data edge case
    print("\n" + "-"*70)
    print("TEST 2: Small Data Edge Case")
    print("-"*70)

    small_data = b"Hi!"
    compressed_small = basic_compressor.compress(small_data)
    decompressed_small = advanced.decompress(compressed_small)

    print(f"Original: {small_data}")
    print(f"Compressed size: {len(compressed_small)} bytes")
    print(f"Decompressed: {decompressed_small}")

    if decompressed_small == small_data:
        print("[SUCCESS] Small data test passed")
        test2_pass = True
    else:
        print("[FAILED] Small data test failed")
        test2_pass = False

    # Summary
    print("\n" + "="*70)
    print("                        SUMMARY")
    print("="*70)

    if test1_pass and test2_pass:
        print("\nCRITICAL BUG FIX VERIFIED!")
        print("\nThe decompression pipeline is now working:")
        print("1. AdvancedCompressor.decompress() correctly delegates to ContextFlowDecompressor")
        print("2. ContextFlowDecompressor handles CTXF format properly")
        print("3. The fix resolves the issue where decompress() returned data unchanged")

        print("\nKnown Issues Still Present:")
        print("- TurboCompressor only compresses first block (parallel processing bug)")
        print("- QuantumCompressor has similar block handling issues")
        print("- These are separate bugs in the compressor implementations")
        print("  and don't affect the main decompression fix")
    else:
        print("\nTests failed - further investigation needed")

    return test1_pass and test2_pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)