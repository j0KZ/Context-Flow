/**
 * ContextFlow C Library
 * High-performance compression with KB-scale memory footprint
 * Version 4.0.0 - Q1 2025
 */

#ifndef CONTEXTFLOW_H
#define CONTEXTFLOW_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* Version information */
#define CONTEXTFLOW_VERSION_MAJOR 4
#define CONTEXTFLOW_VERSION_MINOR 0
#define CONTEXTFLOW_VERSION_PATCH 0
#define CONTEXTFLOW_VERSION_STRING "4.0.0"

/* Error codes */
typedef enum {
    CF_SUCCESS = 0,
    CF_ERROR_INVALID_INPUT = -1,
    CF_ERROR_OUT_OF_MEMORY = -2,
    CF_ERROR_COMPRESSION_FAILED = -3,
    CF_ERROR_DECOMPRESSION_FAILED = -4,
    CF_ERROR_INVALID_FORMAT = -5,
    CF_ERROR_CHECKSUM_MISMATCH = -6,
    CF_ERROR_UNSUPPORTED_MODE = -7,
    CF_ERROR_IO_FAILURE = -8
} cf_error_t;

/* Compression modes */
typedef enum {
    CF_MODE_STANDARD = 0,
    CF_MODE_TURBO = 1,
    CF_MODE_QUANTUM = 2,
    CF_MODE_STREAMING = 3,
    CF_MODE_DELTA = 4,
    CF_MODE_DICTIONARY = 5
} cf_mode_t;

/* Compression levels (1-9) */
typedef enum {
    CF_LEVEL_FASTEST = 1,
    CF_LEVEL_FAST = 3,
    CF_LEVEL_DEFAULT = 6,
    CF_LEVEL_BETTER = 7,
    CF_LEVEL_BEST = 9
} cf_level_t;

/* Statistics structure */
typedef struct {
    uint64_t original_size;
    uint64_t compressed_size;
    double compression_ratio;
    double compression_speed_mbps;
    double decompression_speed_mbps;
    uint64_t memory_used;
    uint32_t checksum;
} cf_stats_t;

/* Compression context */
typedef struct cf_context cf_context_t;

/* Stream callback for progressive compression */
typedef int (*cf_stream_callback)(const uint8_t* data, size_t size, void* user_data);

/* ============================================================================
 * Core API Functions
 * ============================================================================ */

/**
 * Initialize the ContextFlow library
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_init(void);

/**
 * Cleanup the ContextFlow library
 */
void cf_cleanup(void);

/**
 * Get version string
 * @return Version string (e.g., "4.0.0")
 */
const char* cf_version(void);

/**
 * Get error description
 * @param error Error code
 * @return Human-readable error description
 */
const char* cf_error_string(cf_error_t error);

/* ============================================================================
 * Simple API - Single-call compression/decompression
 * ============================================================================ */

/**
 * Compress data in a single call
 * @param input Input data buffer
 * @param input_size Size of input data
 * @param output Output buffer (must be allocated by caller)
 * @param output_size Pointer to output buffer size (in/out)
 * @param level Compression level (1-9)
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_compress(
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size,
    cf_level_t level
);

/**
 * Decompress data in a single call
 * @param input Compressed data buffer
 * @param input_size Size of compressed data
 * @param output Output buffer (must be allocated by caller)
 * @param output_size Pointer to output buffer size (in/out)
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_decompress(
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
);

/**
 * Get maximum compressed size for given input size
 * @param input_size Size of input data
 * @return Maximum possible compressed size
 */
size_t cf_compress_bound(size_t input_size);

/* ============================================================================
 * Advanced API - Context-based compression with modes
 * ============================================================================ */

/**
 * Create compression context
 * @param mode Compression mode
 * @param level Compression level
 * @return Context handle or NULL on failure
 */
cf_context_t* cf_create_context(cf_mode_t mode, cf_level_t level);

/**
 * Destroy compression context
 * @param ctx Context handle
 */
void cf_destroy_context(cf_context_t* ctx);

/**
 * Compress data using context
 * @param ctx Context handle
 * @param input Input data
 * @param input_size Input size
 * @param output Output buffer
 * @param output_size Output size (in/out)
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_compress_ctx(
    cf_context_t* ctx,
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
);

/**
 * Decompress data using context
 * @param ctx Context handle
 * @param input Compressed data
 * @param input_size Input size
 * @param output Output buffer
 * @param output_size Output size (in/out)
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_decompress_ctx(
    cf_context_t* ctx,
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
);

/**
 * Reset context for reuse
 * @param ctx Context handle
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_reset_context(cf_context_t* ctx);

/**
 * Get compression statistics
 * @param ctx Context handle
 * @param stats Pointer to statistics structure
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_get_stats(cf_context_t* ctx, cf_stats_t* stats);

/* ============================================================================
 * Streaming API - Progressive compression
 * ============================================================================ */

/**
 * Begin streaming compression
 * @param ctx Context handle
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_stream_begin(cf_context_t* ctx);

/**
 * Process chunk in streaming mode
 * @param ctx Context handle
 * @param input Input chunk
 * @param input_size Chunk size
 * @param output Output buffer
 * @param output_size Output size (in/out)
 * @param finished True if this is the last chunk
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_stream_process(
    cf_context_t* ctx,
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size,
    bool finished
);

/**
 * End streaming compression
 * @param ctx Context handle
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_stream_end(cf_context_t* ctx);

/* ============================================================================
 * Dictionary API - Shared dictionaries for similar files
 * ============================================================================ */

/**
 * Build dictionary from sample files
 * @param samples Array of sample data buffers
 * @param sample_sizes Array of sample sizes
 * @param num_samples Number of samples
 * @param dict Output dictionary buffer
 * @param dict_size Dictionary size (in/out)
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_build_dictionary(
    const uint8_t** samples,
    const size_t* sample_sizes,
    size_t num_samples,
    uint8_t* dict,
    size_t* dict_size
);

/**
 * Load dictionary into context
 * @param ctx Context handle
 * @param dict Dictionary data
 * @param dict_size Dictionary size
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_load_dictionary(
    cf_context_t* ctx,
    const uint8_t* dict,
    size_t dict_size
);

/* ============================================================================
 * Delta API - Version control optimization
 * ============================================================================ */

/**
 * Compute delta between two versions
 * @param base Base version data
 * @param base_size Base size
 * @param target Target version data
 * @param target_size Target size
 * @param delta Output delta buffer
 * @param delta_size Delta size (in/out)
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_compute_delta(
    const uint8_t* base,
    size_t base_size,
    const uint8_t* target,
    size_t target_size,
    uint8_t* delta,
    size_t* delta_size
);

/**
 * Apply delta to base version
 * @param base Base version data
 * @param base_size Base size
 * @param delta Delta data
 * @param delta_size Delta size
 * @param output Output buffer
 * @param output_size Output size (in/out)
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_apply_delta(
    const uint8_t* base,
    size_t base_size,
    const uint8_t* delta,
    size_t delta_size,
    uint8_t* output,
    size_t* output_size
);

/* ============================================================================
 * File API - Direct file compression
 * ============================================================================ */

/**
 * Compress file
 * @param input_path Input file path
 * @param output_path Output file path
 * @param level Compression level
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_compress_file(
    const char* input_path,
    const char* output_path,
    cf_level_t level
);

/**
 * Decompress file
 * @param input_path Input file path
 * @param output_path Output file path
 * @return CF_SUCCESS on success, error code otherwise
 */
cf_error_t cf_decompress_file(
    const char* input_path,
    const char* output_path
);

#ifdef __cplusplus
}
#endif

#endif /* CONTEXTFLOW_H */