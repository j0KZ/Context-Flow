# ContextFlow API Documentation

## Table of Contents
- [Quick Start](#quick-start)
- [Main Functions](#main-functions)
- [Compressor Class](#compressor-class)
- [Decompressor Class](#decompressor-class)
- [Data Detection](#data-detection)
- [Preprocessing](#preprocessing)
- [Context Modeling](#context-modeling)
- [CLI Interface](#cli-interface)

## Quick Start

```python
import contextflow

# Simple compression
compressed = contextflow.compress(data)
decompressed = contextflow.decompress(compressed)
```

## Main Functions

### `compress(data, mode='balanced', fast_mode=False)`

Compress data using ContextFlow algorithm.

**Parameters:**
- `data` (bytes or str): Input data to compress. If str, interpreted as file path.
- `mode` (str): Compression mode - 'fast', 'balanced', or 'max_compression'
- `fast_mode` (bool): Skip neural mixing for speed

**Returns:**
- bytes: Compressed data

**Example:**
```python
# Compress bytes
data = b"Hello, World!" * 100
compressed = contextflow.compress(data)

# Compress file
compressed = contextflow.compress("path/to/file.txt")

# Fast compression
compressed = contextflow.compress(data, mode='fast', fast_mode=True)
```

### `decompress(compressed_data)`

Decompress ContextFlow compressed data.

**Parameters:**
- `compressed_data` (bytes): Compressed data

**Returns:**
- bytes: Original decompressed data

**Example:**
```python
decompressed = contextflow.decompress(compressed_data)
```

## Compressor Class

### `ContextFlowCompressor(mode='balanced', fast_mode=False)`

Main compressor class with full control over compression.

**Parameters:**
- `mode` (str): Compression mode
- `fast_mode` (bool): Enable fast mode

**Attributes:**
- `block_size` (int): Size of compression blocks
- `memory_limit` (int): Maximum memory usage in bytes

**Methods:**

#### `compress(data)`
Compress data with current settings.

```python
compressor = ContextFlowCompressor(mode='max_compression')
compressed = compressor.compress(data)
```

## Decompressor Class

### `ContextFlowDecompressor()`

Main decompressor class.

**Methods:**

#### `decompress(compressed_data)`
Decompress ContextFlow compressed data.

```python
decompressor = ContextFlowDecompressor()
decompressed = decompressor.decompress(compressed)
```

## Data Detection

### `DataDetector()`

Intelligent data type detection.

**Methods:**

#### `detect(data, sample_size=8192)`
Detect data type and metadata.

**Returns:**
- (DataType, dict): Data type enum and metadata

```python
from contextflow.src.data_detector import DataDetector, DataType

detector = DataDetector()
data_type, metadata = detector.detect(data)

if data_type == DataType.JSON_DATA:
    print(f"JSON with {metadata['structure']['keys']} keys")
```

### DataType Enum

```python
class DataType(Enum):
    TEXT = 'text'
    CODE = 'code'
    JSON_DATA = 'json'
    XML_DATA = 'xml'
    CSV_DATA = 'csv'
    BINARY = 'binary'
    MIXED = 'mixed'
```

## Preprocessing

### `BurrowsWheelerTransform(block_size=10000)`

BWT implementation for text preprocessing.

**Methods:**

#### `transform(data)`
Apply BWT to data.

**Returns:**
- (bytes, list): Transformed data and indices

```python
from contextflow.src.preprocessing import BurrowsWheelerTransform

bwt = BurrowsWheelerTransform()
transformed, indices = bwt.transform(data)
restored = bwt.inverse_transform(transformed, indices)
```

### `SlidingWindowDeduplicator(window_size=1024, min_match=32)`

Deduplication with sliding window.

**Methods:**

#### `deduplicate(data)`
Find and remove duplicate sequences.

**Returns:**
- (bytes, list): Deduplicated data and references

```python
from contextflow.src.preprocessing import SlidingWindowDeduplicator

dedup = SlidingWindowDeduplicator()
deduplicated, refs = dedup.deduplicate(data)
restored = dedup.restore(deduplicated, refs)
```

## Context Modeling

### `ContextModel(max_order=4, table_size=1048576)`

Multi-order context modeling.

**Methods:**

#### `update(byte, data_type)`
Update context with new byte.

#### `predict(data_type)`
Get probability distribution for next byte.

**Returns:**
- np.ndarray: Probability distribution (256 values)

```python
from contextflow.src.context_model import ContextModel

model = ContextModel(max_order=4)
for byte in data:
    prediction = model.predict('text')
    model.update(byte, 'text')
```

### Specialized Contexts

```python
from contextflow.src.context_model import CodeContext, JSONContext

# Code-specific context
code_ctx = CodeContext()
code_ctx.update(byte)
prediction = code_ctx.get_prediction()

# JSON-specific context
json_ctx = JSONContext()
json_ctx.update(byte)
prediction = json_ctx.get_prediction()
```

## Neural Mixer

### `FastNeuralMixer(input_size=16, hidden_size=32, output_size=256)`

Lightweight neural network for context mixing.

**Methods:**

#### `forward(inputs)`
Forward pass through network.

#### `train_step(inputs, target, prediction)`
Single training step.

```python
from contextflow.src.neural_mixer import FastNeuralMixer
import numpy as np

mixer = FastNeuralMixer()
inputs = np.random.randn(16).astype(np.float32)
output = mixer.forward(inputs)
```

## Entropy Coding

### `TANSEncoder(state_bits=12)`

tANS entropy encoder.

**Methods:**

#### `encode_block(data, probabilities)`
Encode data with given probabilities.

```python
from contextflow.src.tans_coder import TANSEncoder
import numpy as np

encoder = TANSEncoder()
probs = np.ones(256) / 256
encoded = encoder.encode_block(data, probs)
```

### `AdaptiveANS(window_size=4096)`

Adaptive tANS with probability updates.

```python
from contextflow.src.tans_coder import AdaptiveANS

coder = AdaptiveANS()
encoded = coder.encode_adaptive(data)
decoded = coder.decode_adaptive(encoded, original_length)
```

## CLI Interface

### Commands

#### compress
```bash
contextflow compress [OPTIONS] INPUT

Options:
  -o, --output PATH     Output file path
  -m, --mode MODE       Compression mode (fast/balanced/max)
  --fast               Enable fast mode
  -v, --verbose        Verbose output
```

#### decompress
```bash
contextflow decompress [OPTIONS] INPUT

Options:
  -o, --output PATH     Output file path
  -v, --verbose        Verbose output
```

#### benchmark
```bash
contextflow benchmark [OPTIONS] INPUT

Options:
  --compare COMPRESSOR  Compare with other compressors
  --iterations N        Number of iterations
```

#### info
```bash
contextflow info INPUT
```

### Examples

```bash
# Compress file
contextflow compress input.txt -o output.ctxf

# Fast compression
contextflow compress -m fast --fast large_file.json

# Decompress
contextflow decompress compressed.ctxf

# Benchmark
contextflow benchmark test.txt --compare gzip bzip2 zstd

# Get file info
contextflow info compressed.ctxf
```

## Advanced Usage

### Custom Block Size

```python
compressor = ContextFlowCompressor()
compressor.block_size = 512 * 1024  # 512KB blocks
```

### Memory Limits

```python
compressor = ContextFlowCompressor()
compressor.memory_limit = 128 * 1024 * 1024  # 128MB limit
```

### Streaming Compression

```python
def compress_stream(input_stream, output_stream, chunk_size=65536):
    compressor = ContextFlowCompressor()

    while True:
        chunk = input_stream.read(chunk_size)
        if not chunk:
            break

        compressed = compressor.compress(chunk)
        output_stream.write(len(compressed).to_bytes(4, 'little'))
        output_stream.write(compressed)
```

### Progress Callbacks

```python
def compress_with_progress(data, callback=None):
    compressor = ContextFlowCompressor()
    total_size = len(data)
    processed = 0

    for i in range(0, total_size, compressor.block_size):
        block = data[i:i + compressor.block_size]
        compressed_block = compressor.compress(block)

        processed += len(block)
        if callback:
            callback(processed, total_size)

    return compressed_data
```

## Error Handling

```python
try:
    compressed = contextflow.compress(data)
    decompressed = contextflow.decompress(compressed)
except ValueError as e:
    print(f"Compression error: {e}")
except MemoryError as e:
    print(f"Memory limit exceeded: {e}")
```

## File Format

### Header Structure
```
Offset | Size | Description
-------|------|-------------
0      | 4    | Magic: 'CTXF'
4      | 1    | Version
5      | 1    | Flags
6      | 2    | Block size (KB)
8      | 4    | Data size
12     | 4    | Metadata size
16     | N    | JSON metadata
16+N   | M    | Compressed data
16+N+M | 4    | SHA-256 checksum
```

### Flags Byte
```
Bit | Description
----|-------------
0   | Fast mode
1   | Max compression
2-7 | Reserved
```

## Performance Tips

1. **Choose appropriate mode**: Fast for speed, max for ratio
2. **Use fast_mode**: When neural mixing isn't needed
3. **Adjust block size**: Larger blocks for better ratio
4. **Preprocess data**: Sort similar data together
5. **Batch operations**: Compress multiple files together

## Thread Safety

ContextFlow is NOT thread-safe. For concurrent use:

```python
import threading

# Create separate compressor per thread
local = threading.local()

def get_compressor():
    if not hasattr(local, 'compressor'):
        local.compressor = ContextFlowCompressor()
    return local.compressor

def compress_thread_safe(data):
    return get_compressor().compress(data)
```

## Version Compatibility

- Files compressed with v1.0.x can be decompressed with any v1.x.x
- Major version changes may break compatibility
- Use `contextflow info` to check file version