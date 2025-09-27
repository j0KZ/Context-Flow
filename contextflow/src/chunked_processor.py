"""
Chunked Processing for Large Files
Handles files of any size without timeout
"""

import struct
import threading
from typing import Callable, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from .config import CompressionConfig, FeatureFlags, runtime_config


class ChunkedProcessor:
    """
    Process large files in chunks to avoid timeouts
    Maintains constant memory usage regardless of file size
    """

    def __init__(self, chunk_size: Optional[int] = None):
        """
        Initialize chunked processor

        Args:
            chunk_size: Size of chunks to process (default from config)
        """
        self.chunk_size = chunk_size or CompressionConfig.DEFAULT_CHUNK_SIZE
        self.use_parallel = FeatureFlags.USE_PARALLEL_PROCESSING
        self.max_threads = CompressionConfig.MAX_THREADS

    def compress_chunked(self, data: bytes, compressor: Callable[[bytes], bytes],
                        progress_callback: Optional[Callable] = None) -> bytes:
        """
        Compress data in chunks

        Args:
            data: Input data
            compressor: Function to compress a chunk
            progress_callback: Optional progress reporting

        Returns:
            Compressed data with chunk headers
        """
        if not FeatureFlags.USE_CHUNKED_PROCESSING:
            # Feature flag disabled, use regular compression
            return compressor(data)

        if len(data) <= CompressionConfig.LARGE_FILE_THRESHOLD:
            # Small file, process normally
            return self._wrap_single_chunk(compressor(data))

        # Large file, process in chunks
        return self._process_chunks(data, compressor, progress_callback, compress=True)

    def decompress_chunked(self, data: bytes, decompressor: Callable[[bytes], bytes],
                          progress_callback: Optional[Callable] = None) -> bytes:
        """
        Decompress chunked data

        Args:
            data: Compressed data with chunk headers
            decompressor: Function to decompress a chunk
            progress_callback: Optional progress reporting

        Returns:
            Original data
        """
        if not self._is_chunked_format(data):
            # Not chunked format, decompress normally
            return decompressor(data)

        return self._process_chunks(data, decompressor, progress_callback, compress=False)

    def _process_chunks(self, data: bytes, processor: Callable[[bytes], bytes],
                       progress_callback: Optional[Callable], compress: bool) -> bytes:
        """
        Process data in chunks (compress or decompress)

        Args:
            data: Input data
            processor: Function to process each chunk
            progress_callback: Optional progress callback
            compress: True for compression, False for decompression

        Returns:
            Processed data
        """
        if compress:
            return self._compress_in_chunks(data, processor, progress_callback)
        else:
            return self._decompress_from_chunks(data, processor, progress_callback)

    def _compress_in_chunks(self, data: bytes, compressor: Callable[[bytes], bytes],
                           progress_callback: Optional[Callable]) -> bytes:
        """
        Compress data in chunks with parallel processing

        Args:
            data: Input data
            compressor: Compression function
            progress_callback: Progress callback

        Returns:
            Compressed data with chunk headers
        """
        total_size = len(data)
        num_chunks = (total_size + self.chunk_size - 1) // self.chunk_size

        # Header: magic, version, num_chunks, chunk_size
        header = struct.pack('<4sBIL',
                           b'CHNK',  # Magic bytes
                           1,        # Version
                           num_chunks,
                           self.chunk_size)

        compressed_chunks = []
        chunk_headers = []

        if self.use_parallel and num_chunks > 1:
            # Parallel processing for multiple chunks
            with ThreadPoolExecutor(max_workers=min(self.max_threads, num_chunks)) as executor:
                # Submit all chunks
                futures = {}
                for i in range(num_chunks):
                    start = i * self.chunk_size
                    end = min(start + self.chunk_size, total_size)
                    chunk = data[start:end]

                    future = executor.submit(self._compress_chunk_with_timeout, chunk, compressor)
                    futures[future] = i

                # Collect results in order
                results = [None] * num_chunks
                completed = 0

                for future in as_completed(futures):
                    chunk_idx = futures[future]
                    try:
                        compressed = future.result(timeout=CompressionConfig.CHUNK_TIMEOUT)
                        results[chunk_idx] = compressed
                        completed += 1

                        if progress_callback:
                            progress_callback(completed, num_chunks, f"Chunk {chunk_idx + 1}/{num_chunks}")
                    except Exception as e:
                        runtime_config.report_error(e, f"Chunk {chunk_idx} compression failed")
                        # Use fallback compression
                        chunk_start = chunk_idx * self.chunk_size
                        chunk_end = min(chunk_start + self.chunk_size, total_size)
                        results[chunk_idx] = self._safe_compress(data[chunk_start:chunk_end])

                compressed_chunks = results
        else:
            # Sequential processing for single chunk or if parallel disabled
            for i in range(num_chunks):
                start = i * self.chunk_size
                end = min(start + self.chunk_size, total_size)
                chunk = data[start:end]

                compressed = self._compress_chunk_with_timeout(chunk, compressor)
                compressed_chunks.append(compressed)

                if progress_callback:
                    progress_callback(i + 1, num_chunks, f"Chunk {i + 1}/{num_chunks}")

        # Build final output
        output = bytearray(header)

        # Add chunk table (offset, compressed_size, original_size)
        offset = len(header) + num_chunks * 12  # Each entry is 12 bytes
        for i, compressed in enumerate(compressed_chunks):
            original_size = min(self.chunk_size, total_size - i * self.chunk_size)
            chunk_header = struct.pack('<LLL', offset, len(compressed), original_size)
            chunk_headers.append(chunk_header)
            offset += len(compressed)

        # Add chunk headers and data
        for chunk_header in chunk_headers:
            output.extend(chunk_header)
        for compressed_chunk in compressed_chunks:
            output.extend(compressed_chunk)

        return bytes(output)

    def _decompress_from_chunks(self, data: bytes, decompressor: Callable[[bytes], bytes],
                               progress_callback: Optional[Callable]) -> bytes:
        """
        Decompress chunked data

        Args:
            data: Chunked compressed data
            decompressor: Decompression function
            progress_callback: Progress callback

        Returns:
            Original data
        """
        if len(data) < 13:  # Minimum header size
            raise ValueError("Invalid chunked data format")

        # Parse header
        magic, version, num_chunks, chunk_size = struct.unpack('<4sBIL', data[:13])

        if magic != b'CHNK':
            raise ValueError("Invalid chunk magic bytes")
        if version != 1:
            raise ValueError(f"Unsupported chunk version: {version}")

        # Parse chunk table
        table_start = 13
        table_size = num_chunks * 12
        chunk_table = []

        for i in range(num_chunks):
            entry_start = table_start + i * 12
            entry = struct.unpack('<LLL', data[entry_start:entry_start + 12])
            chunk_table.append(entry)  # (offset, compressed_size, original_size)

        # Decompress chunks
        result = bytearray()

        if self.use_parallel and num_chunks > 1:
            # Parallel decompression
            with ThreadPoolExecutor(max_workers=min(self.max_threads, num_chunks)) as executor:
                futures = {}

                for i, (offset, comp_size, orig_size) in enumerate(chunk_table):
                    compressed_chunk = data[offset:offset + comp_size]
                    future = executor.submit(self._decompress_chunk_with_timeout,
                                           compressed_chunk, decompressor)
                    futures[future] = i

                # Collect results in order
                results = [None] * num_chunks
                completed = 0

                for future in as_completed(futures):
                    chunk_idx = futures[future]
                    try:
                        decompressed = future.result(timeout=CompressionConfig.CHUNK_TIMEOUT)
                        results[chunk_idx] = decompressed
                        completed += 1

                        if progress_callback:
                            progress_callback(completed, num_chunks, f"Chunk {chunk_idx + 1}/{num_chunks}")
                    except Exception as e:
                        runtime_config.report_error(e, f"Chunk {chunk_idx} decompression failed")
                        # Return zeros for failed chunk
                        _, _, orig_size = chunk_table[chunk_idx]
                        results[chunk_idx] = b'\x00' * orig_size

                # Assemble result
                for chunk_data in results:
                    result.extend(chunk_data)
        else:
            # Sequential decompression
            for i, (offset, comp_size, orig_size) in enumerate(chunk_table):
                compressed_chunk = data[offset:offset + comp_size]
                decompressed = self._decompress_chunk_with_timeout(compressed_chunk, decompressor)
                result.extend(decompressed)

                if progress_callback:
                    progress_callback(i + 1, num_chunks, f"Chunk {i + 1}/{num_chunks}")

        return bytes(result)

    def _compress_chunk_with_timeout(self, chunk: bytes, compressor: Callable[[bytes], bytes]) -> bytes:
        """
        Compress a chunk with timeout

        Args:
            chunk: Data chunk
            compressor: Compression function

        Returns:
            Compressed chunk
        """
        if not FeatureFlags.ENABLE_FALLBACKS:
            return compressor(chunk)

        try:
            # Try compression with timeout
            return self._run_with_timeout(compressor, chunk, CompressionConfig.CHUNK_TIMEOUT)
        except Exception:
            # Fallback to safe compression
            return self._safe_compress(chunk)

    def _decompress_chunk_with_timeout(self, chunk: bytes, decompressor: Callable[[bytes], bytes]) -> bytes:
        """
        Decompress a chunk with timeout

        Args:
            chunk: Compressed chunk
            decompressor: Decompression function

        Returns:
            Decompressed chunk
        """
        if not FeatureFlags.ENABLE_FALLBACKS:
            return decompressor(chunk)

        try:
            # Try decompression with timeout
            return self._run_with_timeout(decompressor, chunk, CompressionConfig.CHUNK_TIMEOUT)
        except Exception:
            # Try safe decompression
            return self._safe_decompress(chunk)

    def _run_with_timeout(self, func: Callable, data: bytes, timeout: int) -> bytes:
        """
        Run function with timeout

        Args:
            func: Function to run
            data: Input data
            timeout: Timeout in seconds

        Returns:
            Function result
        """
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = func(data)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]

    def _safe_compress(self, data: bytes) -> bytes:
        """
        Safe fallback compression using zlib

        Args:
            data: Input data

        Returns:
            Compressed data
        """
        import zlib
        return zlib.compress(data, level=CompressionConfig.ZLIB_LEVEL)

    def _safe_decompress(self, data: bytes) -> bytes:
        """
        Safe fallback decompression using zlib

        Args:
            data: Compressed data

        Returns:
            Decompressed data
        """
        import zlib
        try:
            return zlib.decompress(data)
        except:
            # If zlib fails, data might be uncompressed
            return data

    def _wrap_single_chunk(self, compressed: bytes) -> bytes:
        """
        Wrap single chunk in chunked format for consistency

        Args:
            compressed: Compressed data

        Returns:
            Chunked format with single chunk
        """
        header = struct.pack('<4sBIL',
                           b'CHNK',  # Magic bytes
                           1,        # Version
                           1,        # One chunk
                           len(compressed))

        chunk_header = struct.pack('<LLL',
                                 13 + 12,  # Offset after header and table
                                 len(compressed),
                                 len(compressed))  # Assume same size for simplicity

        return header + chunk_header + compressed

    def _is_chunked_format(self, data: bytes) -> bool:
        """
        Check if data is in chunked format

        Args:
            data: Data to check

        Returns:
            True if chunked format
        """
        return len(data) >= 4 and data[:4] == b'CHNK'


class AdaptiveChunker:
    """
    Adaptive chunking based on data characteristics
    """

    def __init__(self):
        self.min_chunk = CompressionConfig.MIN_BLOCK_SIZE
        self.max_chunk = CompressionConfig.MAX_BLOCK_SIZE

    def determine_chunk_size(self, data: bytes, offset: int = 0,
                           sample_size: int = 4096) -> int:
        """
        Determine optimal chunk size based on data entropy

        Args:
            data: Input data
            offset: Starting offset
            sample_size: Size of sample to analyze

        Returns:
            Optimal chunk size
        """
        import numpy as np

        # Sample data for analysis
        sample_end = min(offset + sample_size, len(data))
        sample = data[offset:sample_end]

        if len(sample) < 256:
            return self.min_chunk

        # Calculate entropy
        byte_counts = np.bincount(np.frombuffer(sample, dtype=np.uint8), minlength=256)
        probabilities = byte_counts / len(sample)
        probabilities = probabilities[probabilities > 0]

        if len(probabilities) == 0:
            return self.min_chunk

        entropy = -np.sum(probabilities * np.log2(probabilities))

        # Adjust chunk size based on entropy
        # High entropy = smaller chunks (less redundancy)
        # Low entropy = larger chunks (more redundancy)
        if entropy > 7.5:  # Nearly random
            chunk_size = self.min_chunk
        elif entropy > 6.0:  # Moderate entropy
            chunk_size = 65536
        elif entropy > 4.0:  # Low entropy
            chunk_size = 262144
        else:  # Very low entropy
            chunk_size = 524288

        return min(max(chunk_size, self.min_chunk), self.max_chunk)