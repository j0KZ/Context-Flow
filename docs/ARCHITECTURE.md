# ContextFlow Architecture

## Overview

ContextFlow is designed as a modular, memory-efficient compression system that balances compression ratio with practical performance. The architecture prioritizes:

- **Memory Efficiency**: KB-scale operation (not GB)
- **Modularity**: Clear separation between stages
- **Adaptability**: Dynamic adjustment based on data type
- **Robustness**: Fallback mechanisms for edge cases

## System Architecture

```
┌────────────────────────────────────────────────────────┐
│                    ContextFlow Core                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Frontend   │  │   Pipeline   │  │   Backend   │ │
│  │              │  │              │  │             │ │
│  │ • CLI        │  │ • Detector   │  │ • tANS      │ │
│  │ • Python API │  │ • LZ77       │  │ • Range     │ │
│  │ • File I/O   │  │ • Context    │  │ • zlib      │ │
│  └──────────────┘  │ • Neural     │  └─────────────┘ │
│                    └──────────────┘                   │
└────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Detection Layer

**Purpose**: Identify data type for optimized compression strategy

**Components**:
- `DataDetector` class
- Pattern recognition for text/code/JSON/XML/binary
- Entropy analysis
- Statistical profiling

**Memory Usage**: <1KB

**Key Features**:
- O(1) detection with sampling
- Language detection for code
- Structure detection for JSON/XML
- Binary entropy measurement

### 2. Preprocessing Layer

**Purpose**: Transform data for better compressibility

**Components**:

#### LZ77 Deduplication
- **Window Size**: 32KB
- **Min Match**: 4 bytes
- **Max Match**: 258 bytes
- **Hash Table**: O(1) lookups

#### Burrows-Wheeler Transform (Optional)
- **Block Size**: 10KB (reduced for speed)
- **Memory**: O(n) for block
- **Use Case**: Text data only

**Memory Usage**: 32-64KB

### 3. Context Modeling Layer

**Purpose**: Build probability models for prediction

**Components**:

#### Multi-Order Contexts
```python
Order 0: P(byte)
Order 1: P(byte | prev_1)
Order 2: P(byte | prev_2)
Order 3: P(byte | prev_3)
Order 4: P(byte | prev_4)
```

#### Specialized Contexts
- **Text**: Word-level contexts
- **Code**: Keyword/identifier tracking
- **JSON**: Key-value separation
- **Binary**: Byte-pair frequencies

**Memory Usage**: 256KB (64KB per order)

**Hash Table Design**:
```python
class HashTable:
    size = 1 << 20  # 1M entries
    table = uint32[size, 2]  # symbol, count

    def hash(context):
        return fnv1a(context) & mask
```

### 4. Neural Mixing Layer

**Purpose**: Combine context predictions optimally

**Architecture**:
```
Input (16) → Hidden (32) → Output (256)
```

**Components**:
- **Weights**: ~10KB total
- **Activation**: ReLU (fast)
- **Output**: Softmax
- **Learning**: Online SGD with momentum

**Training**:
- **Learning Rate**: 0.01 (adaptive)
- **Momentum**: 0.9
- **Batch Size**: 1 (online)

**Memory Usage**: <10KB

### 5. Entropy Coding Layer

**Purpose**: Convert predictions to compressed bits

**Components**:

#### tANS (Asymmetric Numeral Systems)
- **Table Size**: 2^12 = 4KB
- **State Bits**: 16
- **Renormalization**: Streaming

#### Range Coder (Backup)
- **Precision**: 24 bits
- **Renormalization**: 16 bits

#### zlib (Fallback)
- **Use Case**: Incompressible data
- **Levels**: 1, 6, 9

**Memory Usage**: 4-8KB

## Data Flow

### Compression Pipeline

```
1. Input → Data Detection
   ↓
2. Type-specific preprocessing
   ↓
3. LZ77 deduplication
   ↓
4. Context modeling
   ↓
5. Neural prediction mixing
   ↓
6. Entropy coding
   ↓
7. Output with metadata
```

### Decompression Pipeline

```
1. Parse header/metadata
   ↓
2. Entropy decoding
   ↓
3. Context reconstruction
   ↓
4. LZ77 restoration
   ↓
5. Inverse preprocessing
   ↓
6. Output verification
```

## Memory Layout

### Total Memory Budget: <512KB

```
Context Models:     256KB (50%)
LZ77 Window:        32KB  (6%)
Hash Tables:        128KB (25%)
Neural Network:     10KB  (2%)
Entropy Tables:     8KB   (1.5%)
Working Buffers:    64KB  (12.5%)
Miscellaneous:      14KB  (3%)
─────────────────────────────
Total:              512KB
```

## Optimization Strategies

### Speed Optimizations

1. **Hash Function Selection**
   - FNV-1a for speed
   - xxHash for quality
   - CityHash for distribution

2. **Cache Optimization**
   - Align hash tables to cache lines
   - Prefetch next context
   - Minimize pointer chasing

3. **Vectorization**
   - SIMD for probability updates
   - AVX2 for neural forward pass
   - SSE for entropy coding

### Memory Optimizations

1. **Compact Representations**
   - 16-bit counts (with rescaling)
   - 8-bit probabilities
   - Packed structures

2. **Sharing**
   - Reuse buffers between stages
   - Single allocation pool
   - Memory-mapped files for large data

3. **Streaming**
   - Process in blocks
   - Limited lookahead
   - Incremental updates

## Error Handling

### Robustness Mechanisms

1. **Fallback Chain**
   ```
   tANS → Range Coder → zlib → Store
   ```

2. **Validation**
   - Header checksums
   - Block CRCs
   - Size limits

3. **Recovery**
   - Partial decompression
   - Skip corrupted blocks
   - Error reporting

## File Format Specification

### Header Structure

```
Offset  Size  Description
0       4     Magic: 'CTXF'
4       1     Version (1-255)
5       1     Flags
              Bit 0: Fast mode
              Bit 1: Max compression
              Bit 2: Neural enabled
              Bits 3-7: Reserved
6       2     Block size (KB)
8       4     Original size
12      4     Metadata size
16      N     JSON metadata
16+N    M     Compressed blocks
16+N+M  4     SHA-256 checksum (truncated)
```

### Block Format

```
[1 byte]  Block type
          0x00: Stored
          0x01: LZ77
          0x02: Context
          0x03: Neural
[4 bytes] Block size
[N bytes] Block data
```

## Performance Characteristics

### Time Complexity

| Operation | Complexity |
|-----------|------------|
| Detection | O(1) sampling |
| LZ77 | O(n) with hash |
| Context | O(1) per byte |
| Neural | O(1) forward pass |
| Entropy | O(n) streaming |

### Space Complexity

| Component | Memory |
|-----------|--------|
| Detection | O(1) |
| LZ77 | O(window) |
| Context | O(contexts) |
| Neural | O(params) |
| Entropy | O(alphabet) |

## Comparison with Other Systems

### vs PAQ Family
- **PAQ**: GB memory, days to compress
- **ContextFlow**: KB memory, seconds to compress

### vs LLM-based
- **LLM**: 100GB models, GPU required
- **ContextFlow**: 10KB network, CPU only

### vs Traditional
- **gzip**: No adaptation, simple LZ77
- **ContextFlow**: Adaptive, multi-stage

## Future Architectural Improvements

### Short Term
1. Better hash functions
2. SIMD vectorization
3. Parallel blocks
4. GPU offload

### Long Term
1. Learned indexes
2. Neural architecture search
3. Distributed compression
4. Hardware acceleration

## Conclusion

ContextFlow's architecture achieves its design goals of lightweight memory usage, modular design, and practical performance. The KB-scale footprint makes it suitable for embedded systems while maintaining competitive compression ratios through intelligent adaptation and neural mixing.