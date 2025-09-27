//! ContextFlow Rust Bindings
//!
//! High-performance compression library with KB-scale memory footprint
//!
//! # Examples
//!
//! ```
//! use contextflow::{compress, decompress, Level};
//!
//! let data = b"The quick brown fox jumps over the lazy dog";
//! let compressed = compress(data, Level::Default)?;
//! let decompressed = decompress(&compressed)?;
//! assert_eq!(data, &decompressed[..]);
//! ```

#![cfg_attr(feature = "no_std", no_std)]

#[cfg(feature = "no_std")]
extern crate alloc;

#[cfg(feature = "no_std")]
use alloc::{vec, vec::Vec, string::String, format};

#[cfg(feature = "std")]
use std::{vec, vec::Vec, string::String, format};

use thiserror::Error;

// Include auto-generated bindings
#[allow(non_upper_case_globals)]
#[allow(non_camel_case_types)]
#[allow(non_snake_case)]
#[allow(dead_code)]
mod bindings {
    include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
}

use bindings::*;

/// ContextFlow error types
#[derive(Error, Debug)]
pub enum Error {
    #[error("Invalid input provided")]
    InvalidInput,

    #[error("Out of memory")]
    OutOfMemory,

    #[error("Compression failed")]
    CompressionFailed,

    #[error("Decompression failed")]
    DecompressionFailed,

    #[error("Invalid format")]
    InvalidFormat,

    #[error("Checksum mismatch")]
    ChecksumMismatch,

    #[error("Unsupported mode")]
    UnsupportedMode,

    #[error("I/O failure")]
    IoFailure,

    #[error("Unknown error: {0}")]
    Unknown(i32),
}

impl From<cf_error_t> for Error {
    fn from(err: cf_error_t) -> Self {
        match err {
            CF_ERROR_INVALID_INPUT => Error::InvalidInput,
            CF_ERROR_OUT_OF_MEMORY => Error::OutOfMemory,
            CF_ERROR_COMPRESSION_FAILED => Error::CompressionFailed,
            CF_ERROR_DECOMPRESSION_FAILED => Error::DecompressionFailed,
            CF_ERROR_INVALID_FORMAT => Error::InvalidFormat,
            CF_ERROR_CHECKSUM_MISMATCH => Error::ChecksumMismatch,
            CF_ERROR_UNSUPPORTED_MODE => Error::UnsupportedMode,
            CF_ERROR_IO_FAILURE => Error::IoFailure,
            _ => Error::Unknown(err),
        }
    }
}

/// Result type for ContextFlow operations
pub type Result<T> = core::result::Result<T, Error>;

/// Compression level
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Level {
    Fastest = 1,
    Fast = 3,
    Default = 6,
    Better = 7,
    Best = 9,
}

impl Into<cf_level_t> for Level {
    fn into(self) -> cf_level_t {
        self as cf_level_t
    }
}

/// Compression mode
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Standard = 0,
    Turbo = 1,
    Quantum = 2,
    Streaming = 3,
    Delta = 4,
    Dictionary = 5,
}

impl Into<cf_mode_t> for Mode {
    fn into(self) -> cf_mode_t {
        self as cf_mode_t
    }
}

/// Compression statistics
#[derive(Debug, Clone)]
pub struct Statistics {
    pub original_size: u64,
    pub compressed_size: u64,
    pub compression_ratio: f64,
    pub compression_speed_mbps: f64,
    pub decompression_speed_mbps: f64,
    pub memory_used: u64,
    pub checksum: u32,
}

impl From<cf_stats_t> for Statistics {
    fn from(stats: cf_stats_t) -> Self {
        Statistics {
            original_size: stats.original_size,
            compressed_size: stats.compressed_size,
            compression_ratio: stats.compression_ratio,
            compression_speed_mbps: stats.compression_speed_mbps,
            decompression_speed_mbps: stats.decompression_speed_mbps,
            memory_used: stats.memory_used,
            checksum: stats.checksum,
        }
    }
}

/// Initialize the library (called automatically)
pub fn init() -> Result<()> {
    unsafe {
        let result = cf_init();
        if result == CF_SUCCESS {
            Ok(())
        } else {
            Err(Error::from(result))
        }
    }
}

/// Cleanup the library
pub fn cleanup() {
    unsafe {
        cf_cleanup();
    }
}

/// Get library version
pub fn version() -> String {
    unsafe {
        let version_ptr = cf_version();
        let c_str = std::ffi::CStr::from_ptr(version_ptr);
        c_str.to_string_lossy().into_owned()
    }
}

/// Simple compression function
pub fn compress(data: &[u8], level: Level) -> Result<Vec<u8>> {
    if data.is_empty() {
        return Ok(Vec::new());
    }

    unsafe {
        let max_size = cf_compress_bound(data.len());
        let mut output = vec![0u8; max_size];
        let mut output_size = max_size;

        let result = cf_compress(
            data.as_ptr(),
            data.len(),
            output.as_mut_ptr(),
            &mut output_size as *mut usize,
            level.into(),
        );

        if result == CF_SUCCESS {
            output.truncate(output_size);
            Ok(output)
        } else {
            Err(Error::from(result))
        }
    }
}

/// Simple decompression function
pub fn decompress(data: &[u8]) -> Result<Vec<u8>> {
    if data.is_empty() {
        return Ok(Vec::new());
    }

    unsafe {
        // Estimate decompressed size (can be improved)
        let mut output_size = data.len() * 10;
        let mut output = vec![0u8; output_size];

        let result = cf_decompress(
            data.as_ptr(),
            data.len(),
            output.as_mut_ptr(),
            &mut output_size as *mut usize,
        );

        if result == CF_SUCCESS {
            output.truncate(output_size);
            Ok(output)
        } else {
            Err(Error::from(result))
        }
    }
}

/// Compression context for advanced operations
pub struct Context {
    ctx: *mut cf_context_t,
}

impl Context {
    /// Create a new context with specified mode and level
    pub fn new(mode: Mode, level: Level) -> Result<Self> {
        unsafe {
            let ctx = cf_create_context(mode.into(), level.into());
            if ctx.is_null() {
                Err(Error::OutOfMemory)
            } else {
                Ok(Context { ctx })
            }
        }
    }

    /// Compress data using this context
    pub fn compress(&mut self, data: &[u8]) -> Result<Vec<u8>> {
        if data.is_empty() {
            return Ok(Vec::new());
        }

        unsafe {
            let max_size = cf_compress_bound(data.len());
            let mut output = vec![0u8; max_size];
            let mut output_size = max_size;

            let result = cf_compress_ctx(
                self.ctx,
                data.as_ptr(),
                data.len(),
                output.as_mut_ptr(),
                &mut output_size as *mut usize,
            );

            if result == CF_SUCCESS {
                output.truncate(output_size);
                Ok(output)
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Decompress data using this context
    pub fn decompress(&mut self, data: &[u8]) -> Result<Vec<u8>> {
        if data.is_empty() {
            return Ok(Vec::new());
        }

        unsafe {
            let mut output_size = data.len() * 10;
            let mut output = vec![0u8; output_size];

            let result = cf_decompress_ctx(
                self.ctx,
                data.as_ptr(),
                data.len(),
                output.as_mut_ptr(),
                &mut output_size as *mut usize,
            );

            if result == CF_SUCCESS {
                output.truncate(output_size);
                Ok(output)
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Reset the context for reuse
    pub fn reset(&mut self) -> Result<()> {
        unsafe {
            let result = cf_reset_context(self.ctx);
            if result == CF_SUCCESS {
                Ok(())
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Get compression statistics
    pub fn statistics(&self) -> Result<Statistics> {
        unsafe {
            let mut stats: cf_stats_t = std::mem::zeroed();
            let result = cf_get_stats(self.ctx, &mut stats as *mut cf_stats_t);

            if result == CF_SUCCESS {
                Ok(Statistics::from(stats))
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Load a dictionary for compression
    pub fn load_dictionary(&mut self, dictionary: &[u8]) -> Result<()> {
        unsafe {
            let result = cf_load_dictionary(
                self.ctx,
                dictionary.as_ptr(),
                dictionary.len(),
            );

            if result == CF_SUCCESS {
                Ok(())
            } else {
                Err(Error::from(result))
            }
        }
    }
}

impl Drop for Context {
    fn drop(&mut self) {
        unsafe {
            if !self.ctx.is_null() {
                cf_destroy_context(self.ctx);
            }
        }
    }
}

unsafe impl Send for Context {}
unsafe impl Sync for Context {}

/// Stream compressor for progressive compression
pub struct StreamCompressor {
    context: Context,
}

impl StreamCompressor {
    /// Create a new stream compressor
    pub fn new(level: Level) -> Result<Self> {
        let context = Context::new(Mode::Streaming, level)?;
        Ok(StreamCompressor { context })
    }

    /// Begin streaming compression
    pub fn begin(&mut self) -> Result<()> {
        unsafe {
            let result = cf_stream_begin(self.context.ctx);
            if result == CF_SUCCESS {
                Ok(())
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Process a chunk of data
    pub fn process(&mut self, chunk: &[u8], finished: bool) -> Result<Vec<u8>> {
        unsafe {
            let max_size = cf_compress_bound(chunk.len());
            let mut output = vec![0u8; max_size];
            let mut output_size = max_size;

            let result = cf_stream_process(
                self.context.ctx,
                chunk.as_ptr(),
                chunk.len(),
                output.as_mut_ptr(),
                &mut output_size as *mut usize,
                finished,
            );

            if result == CF_SUCCESS {
                output.truncate(output_size);
                Ok(output)
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// End streaming compression
    pub fn end(&mut self) -> Result<()> {
        unsafe {
            let result = cf_stream_end(self.context.ctx);
            if result == CF_SUCCESS {
                Ok(())
            } else {
                Err(Error::from(result))
            }
        }
    }
}

/// Dictionary builder for training compression dictionaries
pub struct DictionaryBuilder {
    samples: Vec<Vec<u8>>,
}

impl DictionaryBuilder {
    /// Create a new dictionary builder
    pub fn new() -> Self {
        DictionaryBuilder {
            samples: Vec::new(),
        }
    }

    /// Add a sample for dictionary training
    pub fn add_sample(&mut self, sample: Vec<u8>) {
        self.samples.push(sample);
    }

    /// Build a dictionary from the samples
    pub fn build(&self, max_size: usize) -> Result<Vec<u8>> {
        if self.samples.is_empty() {
            return Err(Error::InvalidInput);
        }

        unsafe {
            let sample_ptrs: Vec<*const u8> = self.samples
                .iter()
                .map(|s| s.as_ptr())
                .collect();

            let sample_sizes: Vec<usize> = self.samples
                .iter()
                .map(|s| s.len())
                .collect();

            let mut dictionary = vec![0u8; max_size];
            let mut dict_size = max_size;

            let result = cf_build_dictionary(
                sample_ptrs.as_ptr(),
                sample_sizes.as_ptr(),
                self.samples.len(),
                dictionary.as_mut_ptr(),
                &mut dict_size as *mut usize,
            );

            if result == CF_SUCCESS {
                dictionary.truncate(dict_size);
                Ok(dictionary)
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Clear all samples
    pub fn clear(&mut self) {
        self.samples.clear();
    }
}

/// Delta compression utilities
pub struct Delta;

impl Delta {
    /// Compute delta between two versions
    pub fn compute(base: &[u8], target: &[u8]) -> Result<Vec<u8>> {
        unsafe {
            let mut delta_size = base.len() + target.len();
            let mut delta = vec![0u8; delta_size];

            let result = cf_compute_delta(
                base.as_ptr(),
                base.len(),
                target.as_ptr(),
                target.len(),
                delta.as_mut_ptr(),
                &mut delta_size as *mut usize,
            );

            if result == CF_SUCCESS {
                delta.truncate(delta_size);
                Ok(delta)
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Apply delta to base version
    pub fn apply(base: &[u8], delta: &[u8]) -> Result<Vec<u8>> {
        unsafe {
            let mut output_size = base.len() + delta.len() * 2;
            let mut output = vec![0u8; output_size];

            let result = cf_apply_delta(
                base.as_ptr(),
                base.len(),
                delta.as_ptr(),
                delta.len(),
                output.as_mut_ptr(),
                &mut output_size as *mut usize,
            );

            if result == CF_SUCCESS {
                output.truncate(output_size);
                Ok(output)
            } else {
                Err(Error::from(result))
            }
        }
    }
}

/// File compression utilities
#[cfg(feature = "std")]
pub mod file {
    use super::*;
    use std::path::Path;
    use std::ffi::CString;

    /// Compress a file
    pub fn compress<P: AsRef<Path>>(
        input_path: P,
        output_path: P,
        level: Level,
    ) -> Result<()> {
        let input_cstr = path_to_cstring(input_path)?;
        let output_cstr = path_to_cstring(output_path)?;

        unsafe {
            let result = cf_compress_file(
                input_cstr.as_ptr(),
                output_cstr.as_ptr(),
                level.into(),
            );

            if result == CF_SUCCESS {
                Ok(())
            } else {
                Err(Error::from(result))
            }
        }
    }

    /// Decompress a file
    pub fn decompress<P: AsRef<Path>>(
        input_path: P,
        output_path: P,
    ) -> Result<()> {
        let input_cstr = path_to_cstring(input_path)?;
        let output_cstr = path_to_cstring(output_path)?;

        unsafe {
            let result = cf_decompress_file(
                input_cstr.as_ptr(),
                output_cstr.as_ptr(),
            );

            if result == CF_SUCCESS {
                Ok(())
            } else {
                Err(Error::from(result))
            }
        }
    }

    fn path_to_cstring<P: AsRef<Path>>(path: P) -> Result<CString> {
        let path_str = path.as_ref()
            .to_str()
            .ok_or(Error::InvalidInput)?;

        CString::new(path_str).map_err(|_| Error::InvalidInput)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        let ver = version();
        assert!(ver.starts_with("4."));
    }

    #[test]
    fn test_simple_compression() {
        let data = b"The quick brown fox jumps over the lazy dog";
        let compressed = compress(data, Level::Default).unwrap();
        assert!(compressed.len() < data.len());

        let decompressed = decompress(&compressed).unwrap();
        assert_eq!(data, &decompressed[..]);
    }

    #[test]
    fn test_context() {
        let mut ctx = Context::new(Mode::Standard, Level::Best).unwrap();
        let data = b"Hello, World!";

        let compressed = ctx.compress(data).unwrap();
        let decompressed = ctx.decompress(&compressed).unwrap();

        assert_eq!(data, &decompressed[..]);
    }

    #[test]
    fn test_streaming() {
        let mut streamer = StreamCompressor::new(Level::Fast).unwrap();
        streamer.begin().unwrap();

        let chunk1 = b"First chunk ";
        let chunk2 = b"Second chunk";

        let compressed1 = streamer.process(chunk1, false).unwrap();
        let compressed2 = streamer.process(chunk2, true).unwrap();

        streamer.end().unwrap();

        assert!(!compressed1.is_empty() || !compressed2.is_empty());
    }

    #[test]
    fn test_delta() {
        let v1 = b"The quick brown fox";
        let v2 = b"The quick brown cat";

        let delta = Delta::compute(v1, v2).unwrap();
        assert!(delta.len() < v2.len());

        let reconstructed = Delta::apply(v1, &delta).unwrap();
        assert_eq!(v2, &reconstructed[..]);
    }
}