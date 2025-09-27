"""
ContextFlow Python Library
High-performance compression with KB-scale memory footprint
"""

__version__ = "4.0.0"
__author__ = "ContextFlow Team"

from .core import (
    compress,
    decompress,
    Context,
    StreamCompressor,
    DictionaryBuilder,
    Delta,
    CompressionLevel,
    Mode,
    Statistics,
    __version__ as version,
)

from .exceptions import (
    ContextFlowError,
    InvalidInputError,
    OutOfMemoryError,
    CompressionError,
    DecompressionError,
    InvalidFormatError,
    ChecksumMismatchError,
    UnsupportedModeError,
)

__all__ = [
    # Functions
    "compress",
    "decompress",
    "version",
    # Classes
    "Context",
    "StreamCompressor",
    "DictionaryBuilder",
    "Delta",
    # Enums
    "CompressionLevel",
    "Mode",
    "Statistics",
    # Exceptions
    "ContextFlowError",
    "InvalidInputError",
    "OutOfMemoryError",
    "CompressionError",
    "DecompressionError",
    "InvalidFormatError",
    "ChecksumMismatchError",
    "UnsupportedModeError",
]