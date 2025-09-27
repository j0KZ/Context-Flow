"""Quick test to verify basic functionality works"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test imports
print("Testing imports...")
try:
    from src.advanced_compressor import AdvancedCompressor
    from src.turbo_compressor import TurboCompressor
    from src.quantum_compressor import QuantumCompressor
    print("[OK] All imports successful")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test basic compression
print("\nTesting basic compression...")
try:
    compressor = AdvancedCompressor()
    test_data = b"Hello World! " * 100

    # Standard mode
    compressed = compressor.compress(test_data, mode='standard')
    print(f"[OK] Standard compression: {len(test_data)} -> {len(compressed)} bytes")

    # Streaming mode
    compressed = compressor.compress(test_data, mode='stream')
    print(f"[OK] Streaming compression: {len(compressed)} bytes")

    # Delta mode
    base = b"Version 1"
    target = b"Version 2"
    compressed = compressor.compress(target, mode='delta', base=base)
    print(f"[OK] Delta compression: {len(compressed)} bytes")

    print("\nAll basic tests passed!")

except Exception as e:
    print(f"[FAIL] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)