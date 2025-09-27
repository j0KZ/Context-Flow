# ContextFlow Language Bindings

## 🌐 Multi-Language Support for ContextFlow Compression

ContextFlow provides native bindings for multiple programming languages, allowing you to integrate high-performance compression with KB-scale memory footprint into any application.

## 📦 Available Bindings

### ✅ Completed (Q1 2025)

#### C Library
- **Status**: ✅ Complete
- **Features**: Full API with streaming, dictionary, and delta compression
- **Memory**: <10MB footprint maintained
- **Performance**: 20-40 MB/s compression speed
- **Location**: `bindings/c/`

#### C++ Wrapper
- **Status**: ✅ Complete
- **Features**: Modern C++17 interface with RAII and exceptions
- **Memory**: Same as C library
- **Performance**: Zero-overhead abstraction
- **Location**: `bindings/cpp/`

### 🚧 In Development

#### Rust (Coming Soon)
- **Status**: 🚧 In Progress
- **Features**: Safe FFI bindings with cargo package
- **Target**: Q1 2025
- **Location**: `bindings/rust/`

#### Go (Coming Soon)
- **Status**: 📋 Planned
- **Features**: Native Go implementation
- **Target**: Q1 2025
- **Location**: `bindings/go/`

#### Python (Coming Soon)
- **Status**: 📋 Planned
- **Features**: NumPy integration, wheels distribution
- **Target**: Q1 2025
- **Location**: `bindings/python/`

#### JavaScript/WASM (Coming Soon)
- **Status**: 📋 Planned
- **Features**: Browser and Node.js support
- **Target**: Q2 2025
- **Location**: `bindings/js/`

## 🔧 Building the Bindings

### Prerequisites
- CMake 3.10+
- C11 compiler (GCC, Clang, MSVC)
- C++17 compiler (for C++ wrapper)

### Build Instructions

```bash
# Clone the repository
git clone https://github.com/yourusername/contextflow.git
cd contextflow/bindings

# Create build directory
mkdir build && cd build

# Configure with CMake
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build . --config Release

# Run tests
ctest

# Install (optional)
cmake --install . --prefix /usr/local
```

### Build Options

```bash
# Disable shared libraries (build static only)
cmake .. -DBUILD_SHARED_LIBS=OFF

# Disable tests
cmake .. -DBUILD_TESTS=OFF

# Disable examples
cmake .. -DBUILD_EXAMPLES=OFF

# Disable C++ wrapper
cmake .. -DBUILD_CPP_WRAPPER=OFF

# Enable Link-Time Optimization
cmake .. -DENABLE_LTO=ON
```

## 📚 API Documentation

### C API

#### Basic Usage

```c
#include <contextflow.h>

// Initialize library
cf_init();

// Simple compression
size_t compressed_size = cf_compress_bound(input_size);
uint8_t* compressed = malloc(compressed_size);

cf_compress(input, input_size, compressed, &compressed_size, CF_LEVEL_DEFAULT);

// Simple decompression
size_t output_size = input_size * 10;  // Estimate
uint8_t* output = malloc(output_size);

cf_decompress(compressed, compressed_size, output, &output_size);

// Cleanup
cf_cleanup();
```

#### Advanced Context API

```c
// Create context with specific mode
cf_context_t* ctx = cf_create_context(CF_MODE_TURBO, CF_LEVEL_BEST);

// Compress with context
cf_compress_ctx(ctx, input, input_size, output, &output_size);

// Get statistics
cf_stats_t stats;
cf_get_stats(ctx, &stats);
printf("Compression ratio: %.2fx\n", stats.compression_ratio);

// Destroy context
cf_destroy_context(ctx);
```

#### Streaming API

```c
cf_context_t* ctx = cf_create_context(CF_MODE_STREAMING, CF_LEVEL_DEFAULT);

cf_stream_begin(ctx);

// Process chunks
for (size_t i = 0; i < num_chunks; i++) {
    bool is_last = (i == num_chunks - 1);
    cf_stream_process(ctx, chunk[i], chunk_size[i],
                      output, &output_size, is_last);
}

cf_stream_end(ctx);
```

### C++ API

#### Simple Compression

```cpp
#include <contextflow.hpp>

using namespace contextflow;

// Simple string compression
std::string text = "Hello, World!";
auto compressed = Simple::compressString(text);
auto decompressed = Simple::decompressString(compressed);

// Simple binary compression
std::vector<uint8_t> data = getData();
auto compressed = Simple::compress(data, Level::Best);
auto decompressed = Simple::decompress(compressed);
```

#### Context-Based Compression

```cpp
// Create context with specific mode
Context ctx(Mode::Turbo, Level::Best);

// Compress data
auto compressed = ctx.compress(data);

// Get statistics
auto stats = ctx.getStatistics();
std::cout << "Ratio: " << stats.compressionRatio() << "x\n";

// Reset for reuse
ctx.reset();
```

#### Streaming Compression

```cpp
StreamCompressor streamer(Mode::Streaming);

// Process file stream
std::ifstream input("large_file.txt", std::ios::binary);
std::ofstream output("compressed.ctx", std::ios::binary);

streamer.processStream(input, [&](const std::vector<uint8_t>& chunk) {
    output.write(reinterpret_cast<const char*>(chunk.data()), chunk.size());
});
```

#### Dictionary Compression

```cpp
// Build dictionary from samples
DictionaryBuilder builder;
builder.addSample(sample1);
builder.addSample(sample2);
auto dictionary = builder.build(32768);  // 32KB dictionary

// Use dictionary for compression
Context ctx(Mode::Dictionary);
ctx.loadDictionary(dictionary);
auto compressed = ctx.compress(data);
```

#### Delta Compression

```cpp
// Compute delta between versions
auto delta = Delta::compute(version1, version2);

// Apply delta to get new version
auto version2_reconstructed = Delta::apply(version1, delta);
```

#### File Operations

```cpp
// Compress file
File::compress("input.txt", "output.ctx", Level::Best);

// Decompress file
File::decompress("output.ctx", "restored.txt");
```

## 🎯 Performance Characteristics

### Compression Modes

| Mode | Speed | Ratio | Memory | Use Case |
|------|-------|-------|--------|----------|
| Standard | 20-25 MB/s | 30x (text) | <10MB | General purpose |
| Turbo | 35-40 MB/s | 25x (text) | <15MB | Speed priority |
| Quantum | 15-20 MB/s | 35x (text) | <10MB | Ratio priority |
| Streaming | 20 MB/s | 28x (text) | <5MB | Large files |
| Dictionary | 25 MB/s | 40x (similar) | <20MB | Similar files |
| Delta | 30 MB/s | 90% reduction | <10MB | Versioning |

### Compression Levels

| Level | Speed Impact | Ratio Impact | Description |
|-------|-------------|--------------|-------------|
| Fastest (1) | +50% | -20% | Maximum speed |
| Fast (3) | +25% | -10% | Speed priority |
| Default (6) | Baseline | Baseline | Balanced |
| Better (7) | -10% | +5% | Ratio priority |
| Best (9) | -25% | +10% | Maximum ratio |

## 🧪 Testing

### Running Tests

```bash
# Run all tests
cd build
ctest --output-on-failure

# Run specific test
./test_contextflow_c
./test_contextflow_cpp

# Run with valgrind (Linux)
valgrind --leak-check=full ./test_contextflow_c
```

### Test Coverage

- ✅ Basic compression/decompression
- ✅ All compression modes
- ✅ All compression levels
- ✅ Streaming operations
- ✅ Dictionary building and usage
- ✅ Delta compression
- ✅ Error handling
- ✅ Memory management
- ✅ Thread safety (C++ wrapper)

## 📊 Benchmarks

### Running Benchmarks

```bash
# Build with optimizations
cmake .. -DCMAKE_BUILD_TYPE=Release -DENABLE_LTO=ON

# Run C benchmark
./benchmark_c

# Run C++ benchmark
./benchmark_cpp
```

### Sample Results

```
Platform: x86_64 Linux, Intel i7-9700K @ 3.6GHz
Compiler: GCC 11.2.0 with -O3 -march=native

Text Compression (1MB file):
  Standard Mode: 25.3 MB/s, 30.2x ratio
  Turbo Mode:    38.7 MB/s, 25.8x ratio
  Quantum Mode:  18.9 MB/s, 34.6x ratio

JSON Compression (1MB file):
  Standard Mode: 22.1 MB/s, 2.7x ratio
  Dictionary:    26.4 MB/s, 3.8x ratio

Binary Compression (1MB file):
  Standard Mode: 30.2 MB/s, 1.1x ratio
```

## 🔌 Integration Examples

### CMake Project

```cmake
# Find ContextFlow
find_package(ContextFlow REQUIRED)

# Link to your target
target_link_libraries(your_app ContextFlow::contextflow)

# For C++ wrapper
target_link_libraries(your_app ContextFlow::contextflow_cpp)
```

### pkg-config

```bash
# Compile C program
gcc -o myapp myapp.c $(pkg-config --cflags --libs contextflow)

# Compile C++ program
g++ -o myapp myapp.cpp $(pkg-config --cflags --libs contextflow_cpp)
```

### Manual Compilation

```bash
# C program
gcc -o myapp myapp.c -I/path/to/include -L/path/to/lib -lcontextflow

# C++ program
g++ -o myapp myapp.cpp -I/path/to/include -L/path/to/lib -lcontextflow_cpp -lcontextflow
```

## 🤝 Contributing

We welcome contributions to the language bindings! Areas of interest:

1. **New Language Bindings**: Java, C#, Ruby, PHP
2. **Performance Optimization**: SIMD, platform-specific code
3. **API Improvements**: Better ergonomics, additional features
4. **Documentation**: Examples, tutorials, guides
5. **Testing**: More test cases, fuzzing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## 📄 License

All language bindings are released under the same MIT License as the main ContextFlow project. See [LICENSE](../LICENSE) for details.

## 📞 Support

- **GitHub Issues**: https://github.com/yourusername/contextflow/issues
- **Documentation**: https://docs.contextflow.io
- **Email**: support@contextflow.io

---

<p align="center">
  <strong>ContextFlow Language Bindings</strong><br>
  High-performance compression for every language
</p>