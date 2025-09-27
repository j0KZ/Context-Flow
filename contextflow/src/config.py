"""
ContextFlow Configuration and Feature Flags
Centralized configuration for safe feature rollout
"""

import os
from typing import Optional
import json
from pathlib import Path


class FeatureFlags:
    """
    Feature flags for gradual rollout of new features
    All flags default to safe/stable values
    """

    # Core algorithm flags (default to stable implementations)
    USE_CUSTOM_LZ77 = os.getenv('CTXF_USE_CUSTOM_LZ77', 'false').lower() == 'true'
    USE_HYBRID_ANS = os.getenv('CTXF_USE_HYBRID_ANS', 'false').lower() == 'true'
    USE_CUSTOM_TANS = os.getenv('CTXF_USE_CUSTOM_TANS', 'false').lower() == 'true'

    # Processing flags (default to optimizations on)
    USE_CHUNKED_PROCESSING = os.getenv('CTXF_USE_CHUNKED', 'true').lower() == 'true'
    USE_PARALLEL_PROCESSING = os.getenv('CTXF_USE_PARALLEL', 'true').lower() == 'true'
    USE_SIMD = os.getenv('CTXF_USE_SIMD', 'true').lower() == 'true'

    # Experimental features (default off)
    USE_GPU = os.getenv('CTXF_USE_GPU', 'false').lower() == 'true'
    USE_NEURAL = os.getenv('CTXF_USE_NEURAL', 'false').lower() == 'true'
    USE_STREAMING = os.getenv('CTXF_USE_STREAMING', 'false').lower() == 'true'

    # Safety flags
    ENABLE_FALLBACKS = os.getenv('CTXF_ENABLE_FALLBACKS', 'true').lower() == 'true'
    STRICT_MODE = os.getenv('CTXF_STRICT_MODE', 'false').lower() == 'true'
    DEBUG_MODE = os.getenv('CTXF_DEBUG_MODE', 'false').lower() == 'true'

    @classmethod
    def load_from_file(cls, filepath: Optional[str] = None):
        """Load feature flags from JSON file"""
        if filepath is None:
            filepath = Path.home() / '.contextflow' / 'config.json'

        if not Path(filepath).exists():
            return

        try:
            with open(filepath, 'r') as f:
                config = json.load(f)
                for key, value in config.get('feature_flags', {}).items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)
        except Exception:
            pass  # Silently ignore config errors

    @classmethod
    def to_dict(cls) -> dict:
        """Export current flags as dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if key.isupper() and not key.startswith('_')
        }

    @classmethod
    def safe_mode(cls):
        """Set all flags to safest values"""
        cls.USE_CUSTOM_LZ77 = False
        cls.USE_HYBRID_ANS = False
        cls.USE_CUSTOM_TANS = False
        cls.USE_GPU = False
        cls.USE_NEURAL = False
        cls.ENABLE_FALLBACKS = True

    @classmethod
    def experimental_mode(cls):
        """Enable all experimental features"""
        cls.USE_CUSTOM_LZ77 = True
        cls.USE_HYBRID_ANS = True
        cls.USE_CUSTOM_TANS = True
        cls.USE_GPU = True
        cls.USE_NEURAL = True


class CompressionConfig:
    """
    Compression algorithm configuration parameters
    """

    # Block sizes
    MIN_BLOCK_SIZE = int(os.getenv('CTXF_MIN_BLOCK', '16384'))  # 16KB
    MAX_BLOCK_SIZE = int(os.getenv('CTXF_MAX_BLOCK', '1048576'))  # 1MB
    DEFAULT_CHUNK_SIZE = int(os.getenv('CTXF_CHUNK_SIZE', '65536'))  # 64KB
    LARGE_FILE_THRESHOLD = int(os.getenv('CTXF_LARGE_FILE', '65536'))  # 64KB

    # Threading
    MAX_THREADS = int(os.getenv('CTXF_MAX_THREADS', '8'))
    MIN_PARALLEL_SIZE = int(os.getenv('CTXF_MIN_PARALLEL', '32768'))  # 32KB

    # Compression parameters
    ZLIB_LEVEL = int(os.getenv('CTXF_ZLIB_LEVEL', '6'))
    LZ77_WINDOW_SIZE = int(os.getenv('CTXF_LZ77_WINDOW', '32768'))
    LZ77_MIN_MATCH = int(os.getenv('CTXF_LZ77_MIN_MATCH', '3'))
    LZ77_MAX_MATCH = int(os.getenv('CTXF_LZ77_MAX_MATCH', '258'))

    # ANS parameters
    ANS_STATE_BITS = int(os.getenv('CTXF_ANS_BITS', '12'))
    ANS_BLOCK_SIZE = int(os.getenv('CTXF_ANS_BLOCK', '1024'))

    # Memory limits
    MAX_MEMORY_MB = int(os.getenv('CTXF_MAX_MEMORY_MB', '512'))
    CACHE_SIZE_MB = int(os.getenv('CTXF_CACHE_MB', '64'))

    # Timeouts (in seconds)
    COMPRESSION_TIMEOUT = int(os.getenv('CTXF_TIMEOUT', '300'))  # 5 minutes
    CHUNK_TIMEOUT = int(os.getenv('CTXF_CHUNK_TIMEOUT', '10'))  # 10 seconds

    @classmethod
    def to_dict(cls) -> dict:
        """Export configuration as dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if key.isupper() and not key.startswith('_')
        }

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration values"""
        try:
            assert cls.MIN_BLOCK_SIZE > 0
            assert cls.MAX_BLOCK_SIZE >= cls.MIN_BLOCK_SIZE
            assert cls.MAX_THREADS > 0
            assert cls.ZLIB_LEVEL >= 0 and cls.ZLIB_LEVEL <= 9
            assert cls.LZ77_MIN_MATCH > 0
            assert cls.LZ77_MAX_MATCH >= cls.LZ77_MIN_MATCH
            return True
        except AssertionError:
            return False


class RuntimeConfig:
    """
    Runtime configuration that can be changed during execution
    """

    def __init__(self):
        self.progress_callback = None
        self.error_callback = None
        self.log_level = os.getenv('CTXF_LOG_LEVEL', 'INFO')
        self.metrics_enabled = os.getenv('CTXF_METRICS', 'false').lower() == 'true'
        self.profile_enabled = os.getenv('CTXF_PROFILE', 'false').lower() == 'true'

    def set_progress_callback(self, callback):
        """Set progress reporting callback"""
        self.progress_callback = callback

    def set_error_callback(self, callback):
        """Set error reporting callback"""
        self.error_callback = callback

    def report_progress(self, current: int, total: int, message: str = ""):
        """Report progress if callback is set"""
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def report_error(self, error: Exception, context: str = ""):
        """Report error if callback is set"""
        if self.error_callback:
            self.error_callback(error, context)


# Global runtime config instance
runtime_config = RuntimeConfig()


def get_config_summary() -> dict:
    """Get complete configuration summary"""
    return {
        'feature_flags': FeatureFlags.to_dict(),
        'compression': CompressionConfig.to_dict(),
        'runtime': {
            'log_level': runtime_config.log_level,
            'metrics_enabled': runtime_config.metrics_enabled,
            'profile_enabled': runtime_config.profile_enabled,
        }
    }


def print_config():
    """Print current configuration for debugging"""
    import json
    print("ContextFlow Configuration:")
    print(json.dumps(get_config_summary(), indent=2))


# Load configuration on module import
FeatureFlags.load_from_file()

# Validate configuration
if not CompressionConfig.validate():
    print("Warning: Invalid configuration detected, using defaults")
    # Reset to defaults if invalid
    CompressionConfig.__init__()