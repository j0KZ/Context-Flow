"""
ContextFlow - Advanced hybrid lossless compression system
Combines BWT, context modeling, neural mixing, and tANS entropy coding
"""

__version__ = "1.0.0"
__author__ = "ContextFlow Development"

from .src.compressor import ContextFlowCompressor
from .src.decompressor import ContextFlowDecompressor

def compress(data, mode='balanced', fast_mode=False):
    """
    Compress data using ContextFlow algorithm

    Args:
        data: bytes or file path to compress
        mode: 'balanced', 'max_compression', or 'fast'
        fast_mode: Skip neural mixing for speed

    Returns:
        Compressed bytes
    """
    compressor = ContextFlowCompressor(mode=mode, fast_mode=fast_mode)
    return compressor.compress(data)

def decompress(compressed_data):
    """
    Decompress ContextFlow compressed data

    Args:
        compressed_data: Compressed bytes

    Returns:
        Original data bytes
    """
    decompressor = ContextFlowDecompressor()
    return decompressor.decompress(compressed_data)

__all__ = [
    'ContextFlowCompressor',
    'ContextFlowDecompressor',
    'compress',
    'decompress'
]