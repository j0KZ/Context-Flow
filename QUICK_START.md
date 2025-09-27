# 🚀 ContextFlow Quick Start Guide

## Interactive Demo

Run the interactive demo to try out all features:

```bash
python demo.py
```

## Command Line Usage

### Compress a file:
```bash
python demo.py compress yourfile.txt
```

### Decompress a file:
```bash
python demo.py decompress yourfile.txt.ctx
```

### Test compression:
```bash
python demo.py test yourfile.txt
```

## Python Usage

```python
from contextflow.src.turbo_compressor import TurboCompressor
from contextflow.src.quantum_compressor import QuantumCompressor
from contextflow.src.advanced_compressor import AdvancedCompressor

# Choose your compressor
compressor = QuantumCompressor()  # Best compression ratio
# compressor = TurboCompressor()   # Fast parallel processing
# compressor = AdvancedCompressor() # Smart algorithm selection

# Compress data
data = b"Your data here..."
compressed = compressor.compress(data)
print(f"Compressed from {len(data)} to {len(compressed)} bytes")

# Decompress
decompressed = compressor.decompress(compressed)
assert decompressed == data  # Verify integrity
```

## Try Different Scenarios

### 1. Text Files
```bash
echo "The quick brown fox jumps over the lazy dog" > test.txt
python demo.py compress test.txt
```

### 2. JSON Data
```bash
echo '{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}' > data.json
python demo.py compress data.json
```

### 3. Large Files
```bash
# Create a 100KB test file
python -c "print('Hello World! ' * 10000)" > large.txt
python demo.py compress large.txt
```

## Features to Try

1. **Compare all compressors**: Option 5 in interactive mode
2. **Test custom text**: Option 4 in interactive mode
3. **Batch compression**: Compress multiple files
4. **Performance test**: Use `test_contextflow.py` for benchmarks

## Expected Performance

- **Small files (<10KB)**: 5-10x compression
- **Text files**: 5-15x compression
- **JSON files**: 10-20x compression
- **Repetitive data**: Up to 200x compression
- **Binary files**: 2-5x compression

## Tips

- Use **QuantumCompressor** for best compression ratio
- Use **TurboCompressor** for fastest speed
- Use **AdvancedCompressor** for smart automatic selection
- Files >64KB use automatic chunking (slightly slower but prevents timeouts)

## Run Full Test Suite

```bash
python test_contextflow.py
```

Enjoy exploring ContextFlow! 🎉