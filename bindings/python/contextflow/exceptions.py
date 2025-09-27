"""
ContextFlow Exception Classes
Custom exceptions for the Python bindings
"""


class ContextFlowError(Exception):
    """Base exception for all ContextFlow errors"""
    pass


class InvalidInputError(ContextFlowError):
    """Raised when invalid input is provided"""
    pass


class OutOfMemoryError(ContextFlowError):
    """Raised when system runs out of memory"""
    pass


class CompressionError(ContextFlowError):
    """Raised when compression fails"""
    pass


class DecompressionError(ContextFlowError):
    """Raised when decompression fails"""
    pass


class InvalidFormatError(ContextFlowError):
    """Raised when data format is invalid"""
    pass


class ChecksumMismatchError(ContextFlowError):
    """Raised when checksum verification fails"""
    pass


class UnsupportedModeError(ContextFlowError):
    """Raised when an unsupported mode is requested"""
    pass


class IOError(ContextFlowError):
    """Raised when I/O operations fail"""
    pass