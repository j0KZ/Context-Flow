"""
ContextFlow Compressor - Main compression pipeline
Integrates all compression stages
"""

import struct
import time
import numpy as np
from typing import Dict, Tuple, Optional, Union
import zlib

from .data_detector import DataDetector, DataType
from .preprocessing import Preprocessor
from .context_model import ContextModel, SpecializedContexts
from .neural_mixer import AdaptiveMixer
from .fast_ans import FastANS, StreamingANS


class ContextFlowCompressor:
    """
    Main compressor class that orchestrates the compression pipeline
    """

    MAGIC_HEADER = b'CTXF'
    VERSION = 1

    def __init__(self, mode: str = 'balanced', fast_mode: bool = False):
        """
        Initialize compressor

        Args:
            mode: 'balanced', 'max_compression', or 'fast'
            fast_mode: Skip neural mixing for speed
        """
        self.mode = mode
        self.fast_mode = fast_mode

        # Set block size first
        self.block_size = self._get_block_size()
        self.memory_limit = 256 * 1024 * 1024

        self.detector = DataDetector()
        self.preprocessor = Preprocessor()
        self.context_model = ContextModel(max_order=4 if mode != 'fast' else 2)
        self.specialized_contexts = SpecializedContexts()
        self.mixer = AdaptiveMixer()
        self.entropy_coder = StreamingANS(block_size=self.block_size)

    def _get_block_size(self) -> int:
        """Get block size based on mode"""
        if self.mode == 'fast':
            return 65536
        elif self.mode == 'max_compression':
            return 1048576
        else:
            return 262144

    def compress(self, data: Union[bytes, str]) -> bytes:
        """
        Compress data using ContextFlow algorithm

        Args:
            data: Input data (bytes or file path)

        Returns:
            Compressed data with header and metadata
        """
        if isinstance(data, str):
            with open(data, 'rb') as f:
                data = f.read()

        if not data:
            return self._create_header(0, {}) + b''

        start_time = time.time()

        data_type, type_metadata = self.detector.detect(data)

        blocks = []
        metadata = {
            'data_type': data_type.value,
            'original_size': len(data),
            'blocks': []
        }

        for i in range(0, len(data), self.block_size):
            block = data[i:i + self.block_size]
            compressed_block, block_meta = self._compress_block(block, data_type)

            blocks.append(compressed_block)
            metadata['blocks'].append(block_meta)

            if self.fast_mode:
                continue

            self._update_models(block, data_type)

        compressed_data = b''.join(blocks)

        metadata['compression_time'] = time.time() - start_time
        metadata['compression_ratio'] = len(data) / max(len(compressed_data), 1)

        return self._create_output(compressed_data, metadata)

    def _compress_block(self, block: bytes, data_type: DataType) -> Tuple[bytes, Dict]:
        """Compress a single block"""
        block_meta = {'size': len(block)}

        preprocessed, preprocess_meta = self.preprocessor.preprocess(
            block, data_type.value
        )
        block_meta['preprocessing'] = preprocess_meta

        if data_type == DataType.BINARY and self._is_incompressible(preprocessed):
            return self._store_uncompressed(preprocessed), {'stored': True}

        encoded = self._context_encode(preprocessed, data_type)

        if self.mode == 'max_compression' and len(encoded) > len(block) * 0.9:
            fallback = zlib.compress(block, level=9)
            if len(fallback) < len(encoded):
                return fallback, {'fallback': 'zlib'}

        return encoded, block_meta

    def _context_encode(self, data: bytes, data_type: DataType) -> bytes:
        """Encode using context modeling and tANS"""
        if self.fast_mode:
            # Fast mode: Use streaming ANS directly
            return self.entropy_coder.encode_stream(data)

        # Full mode: Context modeling + ANS
        # Generate predictions from context model
        predictions = []
        self.context_model.reset_if_needed()

        for byte in data[:min(1000, len(data))]:
            self.context_model.update(byte, data_type.value)

        # Use ANS with the collected statistics
        return self.entropy_coder.encode_stream(data)

    def _is_incompressible(self, data: bytes) -> bool:
        """Check if data appears incompressible"""
        if len(data) < 100:
            return False

        sample = data[:min(1000, len(data))]
        unique_bytes = len(set(sample))

        entropy = self._calculate_entropy(sample)

        return entropy > 7.9 and unique_bytes > 250

    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy"""
        if not data:
            return 0.0

        counts = np.bincount(np.frombuffer(data, dtype=np.uint8))
        probs = counts[counts > 0] / len(data)

        return -np.sum(probs * np.log2(probs))

    def _store_uncompressed(self, data: bytes) -> bytes:
        """Store block without compression"""
        return b'\x00' + data

    def _update_models(self, block: bytes, data_type: DataType):
        """Update adaptive models after processing block"""
        sample_size = min(len(block), 1000)
        sample_indices = np.random.choice(len(block), sample_size, replace=False)

        for idx in sample_indices:
            self.context_model.update(block[idx], data_type.value)

    def _create_header(self, size: int, metadata: Dict) -> bytes:
        """Create file header"""
        header = self.MAGIC_HEADER
        header += struct.pack('B', self.VERSION)

        flags = 0
        if self.fast_mode:
            flags |= 0x01
        if self.mode == 'max_compression':
            flags |= 0x02

        header += struct.pack('B', flags)
        header += struct.pack('<H', self.block_size >> 10)
        header += struct.pack('<I', size)

        return header

    def _create_output(self, compressed_data: bytes, metadata: Dict) -> bytes:
        """Create final output with header and metadata"""
        import json

        # Handle empty data case
        if not compressed_data:
            output = bytearray()
            output.extend(self.MAGIC_HEADER)
            output.extend(struct.pack('B', self.VERSION))
            output.extend(struct.pack('B', 0))  # flags
            output.extend(struct.pack('<I', 0))  # size
            return bytes(output)

        meta_json = json.dumps(metadata, separators=(',', ':')).encode('utf-8')
        meta_size = len(meta_json)

        output = bytearray()
        output.extend(self._create_header(len(compressed_data), metadata))
        output.extend(struct.pack('<I', meta_size))
        output.extend(meta_json)
        output.extend(compressed_data)

        import hashlib
        checksum = hashlib.sha256(compressed_data).digest()[:4]
        output.extend(checksum)

        return bytes(output)

    def decompress(self, compressed_data: bytes) -> bytes:
        """
        Decompress data compressed by ContextFlowCompressor

        Args:
            compressed_data: Compressed data with CTXF header

        Returns:
            Original decompressed data
        """
        from .decompressor import ContextFlowDecompressor
        decompressor = ContextFlowDecompressor()
        return decompressor.decompress(compressed_data)