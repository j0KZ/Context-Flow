# ContextFlow API Documentation

## Table of Contents
- [Quick Start](#quick-start)
- [TurboCompressor](#turbocompressor)
- [QuantumCompressor](#quantumcompressor)
- [AdvancedCompressor](#advancedcompressor)
- [Configuration](#configuration)
- [Feature Flags](#feature-flags)

## Quick Start

```python
from contextflow.src.turbo_compressor import TurboCompressor
from contextflow.src.quantum_compressor import QuantumCompressor
from contextflow.src.advanced_compressor import AdvancedCompressor

# Choose your compressor
compressor = QuantumCompressor()  # Best compression ratio
# compressor = TurboCompressor()   # Fast parallel processing
# compressor = AdvancedCompressor() # Smart algorithm selection

# Compress and decompress
data = b"Your data here..."
compressed = compressor.compress(data)
decompressed = compressor.decompress(compressed)
```

## TurboCompressor

Fast parallel compression with 7-10x compression ratios.

### `compress(data: bytes, progress_callback: Optional[Callable] = None) -> bytes`

Compress data using parallel block processing.

**Parameters:**
- `data` (bytes): Input data to compress
- `progress_callback` (callable): Optional callback for progress updates

**Returns:**
- bytes: Compressed data

**Features:**
- Automatic chunking for files >64KB
- Parallel processing with ThreadPoolExecutor
- Fallback to zlib for reliability

**Example:**
```python
from contextflow.src.turbo_compressor import TurboCompressor

compressor = TurboCompressor()
data = b"Hello, World!" * 1000

# Simple compression
compressed = compressor.compress(data)

# With progress tracking
def progress(current, total, message):
    print(f"Progress: {current}/{total} - {message}")

compressed = compressor.compress(data, progress_callback=progress)
```

### `decompress(data: bytes) -> bytes`

Decompress data compressed by TurboCompressor.

**Parameters:**
- `data` (bytes): Compressed data

**Returns:**
- bytes: Decompressed data

## QuantumCompressor

Neural-enhanced compression achieving 9-15x compression ratios.

### `compress(data: bytes) -> bytes`

Compress using neural mixing and range encoding.

**Features:**
- xxHash64 for fast hashing
- Neural context mixing
- 64-bit range arithmetic
- Optimized for text and structured data

**Example:**
```python
from contextflow.src.quantum_compressor import QuantumCompressor

compressor = QuantumCompressor()
data = b"The quick brown fox" * 100

compressed = compressor.compress(data)
print(f"Ratio: {len(data)/len(compressed):.2f}x")
```

## AdvancedCompressor

Smart compression with automatic algorithm selection.

### Methods

- `compress(data: bytes) -> bytes`: Compress using optimal algorithm
- `decompress(data: bytes) -> bytes`: Decompress any supported format
- `compress_streaming(input_stream, output_stream)`: Stream compression
- `compress_with_dictionary(data: bytes, dictionary: bytes) -> bytes`: Dictionary compression
- `compress_delta(base: bytes, target: bytes) -> bytes`: Delta encoding
- `compress_and_encrypt(data: bytes, password: str) -> bytes`: Encrypted compression

**Example:**
```python
from contextflow.src.advanced_compressor import AdvancedCompressor

compressor = AdvancedCompressor()

# Basic compression
compressed = compressor.compress(data)

# Streaming for large files
from io import BytesIO
input_stream = BytesIO(large_data)
output_stream = BytesIO()
compressor.compress_streaming(input_stream, output_stream)

# Delta compression
base_version = b"Version 1.0"
new_version = b"Version 1.1"
delta = compressor.compress_delta(base_version, new_version)
```

## Configuration

### Environment Variables

```bash
# Feature flags
export CTXF_USE_CHUNKED=true         # Enable chunked processing
export CTXF_USE_PARALLEL=true        # Enable parallel compression
export CTXF_ENABLE_FALLBACKS=true    # Enable zlib fallback
export CTXF_USE_CUSTOM_LZ77=false    # Use custom LZ77 (experimental)
export CTXF_USE_GPU=false            # GPU acceleration (experimental)

# Performance tuning
export CTXF_CHUNK_SIZE=65536         # Chunk size in bytes
export CTXF_MAX_THREADS=8            # Max parallel threads
```

### Python Configuration

```python
from contextflow.src.config import FeatureFlags, CompressionConfig

# Enable/disable features
FeatureFlags.USE_CHUNKED_PROCESSING = True
FeatureFlags.USE_PARALLEL_PROCESSING = True
FeatureFlags.ENABLE_FALLBACKS = True

# Safe mode (stable features only)
FeatureFlags.safe_mode()

# Experimental mode (all features)
FeatureFlags.experimental_mode()

# Adjust thresholds
CompressionConfig.LARGE_FILE_THRESHOLD = 100_000  # 100KB
CompressionConfig.CHUNK_SIZE = 32768  # 32KB chunks
```

## Feature Flags

### Safe Mode Features
- Chunked processing for large files
- Parallel compression
- zlib fallback
- Progress callbacks

### Experimental Features
- Custom LZ77 implementation
- GPU acceleration
- Neural pattern learning
- Advanced context modeling

## Error Handling

All compressors provide robust error handling:

```python
try:
    compressed = compressor.compress(data)
    decompressed = compressor.decompress(compressed)
except ValueError as e:
    print(f"Invalid data: {e}")
except MemoryError as e:
    print(f"Out of memory: {e}")
except Exception as e:
    print(f"Compression failed: {e}")
```

## Performance Tips

1. **Choose the right compressor:**
   - TurboCompressor: Best for speed
   - QuantumCompressor: Best compression ratio
   - AdvancedCompressor: Best for mixed data

2. **Large files:**
   - Automatic chunking handles files >64KB
   - Use streaming API for very large files
   - Enable parallel processing for speed

3. **Memory usage:**
   - Chunking keeps memory constant
   - Streaming API for minimal memory
   - Adjust chunk size for your system

4. **Feature flags:**
   - Use safe_mode() for production
   - Test experimental features carefully
   - Monitor performance with different settings