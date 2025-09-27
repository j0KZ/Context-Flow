---
name: Performance issue
about: Report performance problems or suggest optimizations
title: '[PERF] '
labels: performance
assignees: ''

---

**Describe the performance issue**
A clear description of the performance problem you're experiencing.

**Performance metrics**
Provide specific metrics showing the performance issue:
- Compression speed: [e.g., 10 MB/s]
- Decompression speed: [e.g., 15 MB/s]
- Memory usage: [e.g., 500MB]
- Compression ratio: [e.g., 2.5x]

**Expected performance**
What performance level were you expecting based on documentation or similar tools?

**Test data**
Describe the type and size of data you're compressing:
- Data type: [text, JSON, code, binary, etc.]
- File size: [e.g., 100MB]
- Data characteristics: [repetitive, random, structured, etc.]

**Configuration**
```python
# Show how you're using ContextFlow
compressor = ContextFlowCompressor(mode='...', fast_mode=...)
```

**Environment:**
 - OS: [e.g., Ubuntu 22.04]
 - CPU: [e.g., Intel i7-10700K]
 - RAM: [e.g., 16GB]
 - Python version: [e.g., 3.9.0]
 - ContextFlow version: [e.g., 1.0.0]

**Profiling data**
If you've run any profiling tools, please share the results:
```
Paste profiling output here
```

**Comparison with other tools**
If applicable, how does ContextFlow compare to other compression tools on the same data?
- gzip: [speed/ratio]
- bzip2: [speed/ratio]
- zstd: [speed/ratio]

**Suggested optimization**
If you have ideas for improving performance, please describe them here.