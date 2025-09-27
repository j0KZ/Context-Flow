/**
 * ContextFlow C Library Implementation
 * Core compression functionality in pure C
 * Version 4.0.0 - Q1 2025
 */

#include "contextflow.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>

/* ============================================================================
 * Constants and Macros
 * ============================================================================ */

#define MIN_MATCH 3
#define MAX_MATCH 258
#define WINDOW_SIZE 32768
#define HASH_SIZE 65536
#define BLOCK_SIZE 65536
#define MAX_CONTEXTS 256

/* Memory alignment for cache optimization */
#define CACHE_LINE_SIZE 64
#define ALIGN_TO_CACHE(x) (((x) + CACHE_LINE_SIZE - 1) & ~(CACHE_LINE_SIZE - 1))

/* ============================================================================
 * Internal Structures
 * ============================================================================ */

/* LZ77 match structure */
typedef struct {
    uint16_t distance;
    uint8_t length;
} lz77_match_t;

/* Context model for prediction */
typedef struct {
    uint32_t counts[256];
    uint32_t total;
} context_model_t;

/* Range encoder state */
typedef struct {
    uint64_t low;
    uint64_t range;
    uint8_t* buffer;
    size_t buffer_pos;
    size_t buffer_size;
} range_encoder_t;

/* Main compression context */
struct cf_context {
    cf_mode_t mode;
    cf_level_t level;

    /* LZ77 components */
    uint8_t* window;
    size_t window_pos;
    uint16_t* hash_table;
    uint16_t* hash_chain;

    /* Context modeling */
    context_model_t* contexts[4];  /* Order 0-3 contexts */
    uint8_t* history;
    size_t history_pos;

    /* Range coding */
    range_encoder_t encoder;

    /* Statistics */
    cf_stats_t stats;

    /* Dictionary support */
    uint8_t* dictionary;
    size_t dict_size;

    /* Streaming state */
    bool streaming;
    uint8_t* stream_buffer;
    size_t stream_pos;
};

/* ============================================================================
 * Hash Functions
 * ============================================================================ */

static inline uint32_t hash3(const uint8_t* data) {
    /* Simple 3-byte hash using multiplication */
    return ((uint32_t)data[0] * 31 * 31 +
            (uint32_t)data[1] * 31 +
            (uint32_t)data[2]) & (HASH_SIZE - 1);
}

static inline uint32_t xxhash32(const uint8_t* data, size_t len, uint32_t seed) {
    /* Simplified xxHash32 implementation */
    const uint32_t PRIME1 = 0x9E3779B1U;
    const uint32_t PRIME2 = 0x85EBCA77U;
    const uint32_t PRIME3 = 0xC2B2AE3DU;
    const uint32_t PRIME4 = 0x27D4EB2FU;
    const uint32_t PRIME5 = 0x165667B1U;

    uint32_t h32 = seed + PRIME5 + (uint32_t)len;

    const uint8_t* end = data + len;

    while (data + 4 <= end) {
        uint32_t k1 = *(uint32_t*)data;
        k1 *= PRIME2;
        k1 = (k1 << 13) | (k1 >> 19);
        k1 *= PRIME1;

        h32 ^= k1;
        h32 = (h32 << 17) | (h32 >> 15);
        h32 = h32 * PRIME4 + PRIME3;

        data += 4;
    }

    while (data < end) {
        h32 += (*data++) * PRIME5;
        h32 = (h32 << 11) | (h32 >> 21);
        h32 *= PRIME1;
    }

    h32 ^= h32 >> 15;
    h32 *= PRIME2;
    h32 ^= h32 >> 13;
    h32 *= PRIME3;
    h32 ^= h32 >> 16;

    return h32;
}

/* ============================================================================
 * LZ77 Compression
 * ============================================================================ */

static void lz77_init(cf_context_t* ctx) {
    memset(ctx->hash_table, 0xFF, HASH_SIZE * sizeof(uint16_t));
    memset(ctx->hash_chain, 0xFF, WINDOW_SIZE * sizeof(uint16_t));
    ctx->window_pos = 0;
}

static lz77_match_t lz77_find_match(
    cf_context_t* ctx,
    const uint8_t* data,
    size_t pos,
    size_t data_size
) {
    lz77_match_t best = {0, 0};

    if (pos + MIN_MATCH > data_size) {
        return best;
    }

    uint32_t hash = hash3(&data[pos]);
    uint16_t chain_pos = ctx->hash_table[hash];

    int chain_length = ctx->level * 16;  /* Search depth based on level */

    while (chain_pos != 0xFFFF && chain_length-- > 0) {
        if (chain_pos < ctx->window_pos) {
            size_t distance = ctx->window_pos - chain_pos;

            if (distance <= 32768) {
                /* Compare bytes */
                size_t match_len = 0;
                size_t max_len = data_size - pos;
                if (max_len > MAX_MATCH) max_len = MAX_MATCH;

                while (match_len < max_len &&
                       data[pos + match_len] == ctx->window[chain_pos + match_len]) {
                    match_len++;
                }

                if (match_len >= MIN_MATCH && match_len > best.length) {
                    best.distance = (uint16_t)distance;
                    best.length = (uint8_t)match_len;

                    if (match_len >= MAX_MATCH) {
                        break;
                    }
                }
            }
        }

        chain_pos = ctx->hash_chain[chain_pos];
    }

    return best;
}

static void lz77_update_hash(
    cf_context_t* ctx,
    const uint8_t* data,
    size_t pos
) {
    if (pos + MIN_MATCH <= WINDOW_SIZE) {
        uint32_t hash = hash3(&data[pos]);
        ctx->hash_chain[ctx->window_pos] = ctx->hash_table[hash];
        ctx->hash_table[hash] = (uint16_t)ctx->window_pos;

        ctx->window[ctx->window_pos] = data[pos];
        ctx->window_pos = (ctx->window_pos + 1) % WINDOW_SIZE;
    }
}

/* ============================================================================
 * Context Modeling
 * ============================================================================ */

static void context_init(context_model_t* model) {
    for (int i = 0; i < 256; i++) {
        model->counts[i] = 1;  /* Avoid zero probability */
    }
    model->total = 256;
}

static void context_update(context_model_t* model, uint8_t symbol) {
    model->counts[symbol]++;
    model->total++;

    /* Rescale if total gets too large */
    if (model->total > 65536) {
        model->total = 0;
        for (int i = 0; i < 256; i++) {
            model->counts[i] = (model->counts[i] + 1) / 2;
            model->total += model->counts[i];
        }
    }
}

static uint32_t context_get_probability(context_model_t* model, uint8_t symbol) {
    return (model->counts[symbol] << 16) / model->total;
}

/* ============================================================================
 * Range Encoding
 * ============================================================================ */

static void range_encoder_init(range_encoder_t* enc, uint8_t* buffer, size_t size) {
    enc->low = 0;
    enc->range = 0xFFFFFFFF;
    enc->buffer = buffer;
    enc->buffer_pos = 0;
    enc->buffer_size = size;
}

static void range_encoder_encode(
    range_encoder_t* enc,
    uint32_t cum_freq,
    uint32_t freq,
    uint32_t total
) {
    enc->range /= total;
    enc->low += cum_freq * enc->range;
    enc->range *= freq;

    /* Renormalization */
    while (enc->range < 0x1000000) {
        if (enc->buffer_pos < enc->buffer_size) {
            enc->buffer[enc->buffer_pos++] = (uint8_t)(enc->low >> 24);
        }
        enc->low <<= 8;
        enc->range <<= 8;
    }
}

static void range_encoder_finish(range_encoder_t* enc) {
    for (int i = 0; i < 4; i++) {
        if (enc->buffer_pos < enc->buffer_size) {
            enc->buffer[enc->buffer_pos++] = (uint8_t)(enc->low >> 24);
        }
        enc->low <<= 8;
    }
}

/* ============================================================================
 * Core Compression
 * ============================================================================ */

static cf_error_t compress_block(
    cf_context_t* ctx,
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
) {
    size_t in_pos = 0;
    size_t out_pos = 0;
    size_t max_out = *output_size;

    /* Write header */
    if (out_pos + 8 > max_out) return CF_ERROR_OUT_OF_MEMORY;

    output[out_pos++] = 'C';
    output[out_pos++] = 'T';
    output[out_pos++] = 'X';
    output[out_pos++] = 'F';
    output[out_pos++] = (uint8_t)ctx->mode;
    output[out_pos++] = (uint8_t)ctx->level;
    output[out_pos++] = (uint8_t)(input_size >> 8);
    output[out_pos++] = (uint8_t)(input_size & 0xFF);

    /* LZ77 preprocessing for standard and turbo modes */
    if (ctx->mode == CF_MODE_STANDARD || ctx->mode == CF_MODE_TURBO) {
        lz77_init(ctx);

        while (in_pos < input_size) {
            lz77_match_t match = lz77_find_match(ctx, input, in_pos, input_size);

            if (match.length >= MIN_MATCH) {
                /* Encode match */
                if (out_pos + 3 > max_out) return CF_ERROR_OUT_OF_MEMORY;

                output[out_pos++] = 0x80 | match.length;  /* Match marker */
                output[out_pos++] = (uint8_t)(match.distance >> 8);
                output[out_pos++] = (uint8_t)(match.distance & 0xFF);

                /* Update hash for matched bytes */
                for (size_t i = 0; i < match.length; i++) {
                    lz77_update_hash(ctx, input, in_pos + i);
                }
                in_pos += match.length;
            } else {
                /* Encode literal */
                if (out_pos >= max_out) return CF_ERROR_OUT_OF_MEMORY;
                output[out_pos++] = input[in_pos];

                lz77_update_hash(ctx, input, in_pos);
                in_pos++;
            }
        }
    } else {
        /* Simple copy for other modes (placeholder) */
        if (out_pos + input_size > max_out) return CF_ERROR_OUT_OF_MEMORY;
        memcpy(output + out_pos, input, input_size);
        out_pos += input_size;
    }

    /* Update statistics */
    ctx->stats.original_size += input_size;
    ctx->stats.compressed_size += out_pos;

    *output_size = out_pos;
    return CF_SUCCESS;
}

static cf_error_t decompress_block(
    cf_context_t* ctx,
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
) {
    size_t in_pos = 0;
    size_t out_pos = 0;
    size_t max_out = *output_size;

    /* Read and verify header */
    if (input_size < 8) return CF_ERROR_INVALID_FORMAT;

    if (input[0] != 'C' || input[1] != 'T' ||
        input[2] != 'X' || input[3] != 'F') {
        return CF_ERROR_INVALID_FORMAT;
    }

    cf_mode_t mode = (cf_mode_t)input[4];
    cf_level_t level = (cf_level_t)input[5];
    size_t original_size = ((size_t)input[6] << 8) | input[7];
    in_pos = 8;

    if (original_size > max_out) return CF_ERROR_OUT_OF_MEMORY;

    /* Decompress based on mode */
    if (mode == CF_MODE_STANDARD || mode == CF_MODE_TURBO) {
        while (in_pos < input_size && out_pos < original_size) {
            uint8_t byte = input[in_pos++];

            if (byte & 0x80) {
                /* Match */
                uint8_t length = byte & 0x7F;
                if (in_pos + 2 > input_size) return CF_ERROR_INVALID_FORMAT;

                uint16_t distance = ((uint16_t)input[in_pos] << 8) | input[in_pos + 1];
                in_pos += 2;

                if (out_pos < distance) return CF_ERROR_INVALID_FORMAT;

                /* Copy match */
                for (size_t i = 0; i < length; i++) {
                    if (out_pos >= max_out) return CF_ERROR_OUT_OF_MEMORY;
                    output[out_pos] = output[out_pos - distance];
                    out_pos++;
                }
            } else {
                /* Literal */
                if (out_pos >= max_out) return CF_ERROR_OUT_OF_MEMORY;
                output[out_pos++] = byte;
            }
        }
    } else {
        /* Simple copy for other modes (placeholder) */
        size_t copy_size = input_size - in_pos;
        if (copy_size > max_out - out_pos) copy_size = max_out - out_pos;
        memcpy(output + out_pos, input + in_pos, copy_size);
        out_pos += copy_size;
    }

    *output_size = out_pos;
    return CF_SUCCESS;
}

/* ============================================================================
 * Public API Implementation
 * ============================================================================ */

cf_error_t cf_init(void) {
    /* Library initialization */
    return CF_SUCCESS;
}

void cf_cleanup(void) {
    /* Library cleanup */
}

const char* cf_version(void) {
    return CONTEXTFLOW_VERSION_STRING;
}

const char* cf_error_string(cf_error_t error) {
    switch (error) {
        case CF_SUCCESS: return "Success";
        case CF_ERROR_INVALID_INPUT: return "Invalid input";
        case CF_ERROR_OUT_OF_MEMORY: return "Out of memory";
        case CF_ERROR_COMPRESSION_FAILED: return "Compression failed";
        case CF_ERROR_DECOMPRESSION_FAILED: return "Decompression failed";
        case CF_ERROR_INVALID_FORMAT: return "Invalid format";
        case CF_ERROR_CHECKSUM_MISMATCH: return "Checksum mismatch";
        case CF_ERROR_UNSUPPORTED_MODE: return "Unsupported mode";
        case CF_ERROR_IO_FAILURE: return "I/O failure";
        default: return "Unknown error";
    }
}

cf_error_t cf_compress(
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size,
    cf_level_t level
) {
    if (!input || !output || !output_size) {
        return CF_ERROR_INVALID_INPUT;
    }

    cf_context_t* ctx = cf_create_context(CF_MODE_STANDARD, level);
    if (!ctx) {
        return CF_ERROR_OUT_OF_MEMORY;
    }

    cf_error_t result = compress_block(ctx, input, input_size, output, output_size);

    cf_destroy_context(ctx);
    return result;
}

cf_error_t cf_decompress(
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
) {
    if (!input || !output || !output_size) {
        return CF_ERROR_INVALID_INPUT;
    }

    cf_context_t* ctx = cf_create_context(CF_MODE_STANDARD, CF_LEVEL_DEFAULT);
    if (!ctx) {
        return CF_ERROR_OUT_OF_MEMORY;
    }

    cf_error_t result = decompress_block(ctx, input, input_size, output, output_size);

    cf_destroy_context(ctx);
    return result;
}

size_t cf_compress_bound(size_t input_size) {
    /* Conservative estimate: header + worst case (no compression) + some overhead */
    return input_size + (input_size / 16) + 64;
}

cf_context_t* cf_create_context(cf_mode_t mode, cf_level_t level) {
    cf_context_t* ctx = (cf_context_t*)calloc(1, sizeof(cf_context_t));
    if (!ctx) return NULL;

    ctx->mode = mode;
    ctx->level = level;

    /* Allocate window buffer */
    ctx->window = (uint8_t*)malloc(WINDOW_SIZE);
    if (!ctx->window) {
        free(ctx);
        return NULL;
    }

    /* Allocate hash tables */
    ctx->hash_table = (uint16_t*)malloc(HASH_SIZE * sizeof(uint16_t));
    ctx->hash_chain = (uint16_t*)malloc(WINDOW_SIZE * sizeof(uint16_t));

    if (!ctx->hash_table || !ctx->hash_chain) {
        free(ctx->window);
        free(ctx->hash_table);
        free(ctx->hash_chain);
        free(ctx);
        return NULL;
    }

    /* Initialize context models */
    for (int i = 0; i < 4; i++) {
        ctx->contexts[i] = (context_model_t*)calloc(1, sizeof(context_model_t));
        if (ctx->contexts[i]) {
            context_init(ctx->contexts[i]);
        }
    }

    /* Allocate history buffer */
    ctx->history = (uint8_t*)calloc(256, sizeof(uint8_t));

    return ctx;
}

void cf_destroy_context(cf_context_t* ctx) {
    if (!ctx) return;

    free(ctx->window);
    free(ctx->hash_table);
    free(ctx->hash_chain);
    free(ctx->history);
    free(ctx->dictionary);
    free(ctx->stream_buffer);

    for (int i = 0; i < 4; i++) {
        free(ctx->contexts[i]);
    }

    free(ctx);
}

cf_error_t cf_compress_ctx(
    cf_context_t* ctx,
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
) {
    if (!ctx || !input || !output || !output_size) {
        return CF_ERROR_INVALID_INPUT;
    }

    return compress_block(ctx, input, input_size, output, output_size);
}

cf_error_t cf_decompress_ctx(
    cf_context_t* ctx,
    const uint8_t* input,
    size_t input_size,
    uint8_t* output,
    size_t* output_size
) {
    if (!ctx || !input || !output || !output_size) {
        return CF_ERROR_INVALID_INPUT;
    }

    return decompress_block(ctx, input, input_size, output, output_size);
}

cf_error_t cf_reset_context(cf_context_t* ctx) {
    if (!ctx) return CF_ERROR_INVALID_INPUT;

    /* Reset LZ77 state */
    lz77_init(ctx);

    /* Reset context models */
    for (int i = 0; i < 4; i++) {
        if (ctx->contexts[i]) {
            context_init(ctx->contexts[i]);
        }
    }

    /* Clear history */
    if (ctx->history) {
        memset(ctx->history, 0, 256);
    }
    ctx->history_pos = 0;

    /* Clear statistics */
    memset(&ctx->stats, 0, sizeof(cf_stats_t));

    return CF_SUCCESS;
}

cf_error_t cf_get_stats(cf_context_t* ctx, cf_stats_t* stats) {
    if (!ctx || !stats) return CF_ERROR_INVALID_INPUT;

    *stats = ctx->stats;

    /* Calculate compression ratio */
    if (ctx->stats.compressed_size > 0) {
        stats->compression_ratio = (double)ctx->stats.original_size /
                                  (double)ctx->stats.compressed_size;
    }

    return CF_SUCCESS;
}

/* ============================================================================
 * File I/O Implementation
 * ============================================================================ */

cf_error_t cf_compress_file(
    const char* input_path,
    const char* output_path,
    cf_level_t level
) {
    FILE* in_file = fopen(input_path, "rb");
    if (!in_file) return CF_ERROR_IO_FAILURE;

    FILE* out_file = fopen(output_path, "wb");
    if (!out_file) {
        fclose(in_file);
        return CF_ERROR_IO_FAILURE;
    }

    /* Get file size */
    fseek(in_file, 0, SEEK_END);
    size_t file_size = ftell(in_file);
    fseek(in_file, 0, SEEK_SET);

    /* Allocate buffers */
    uint8_t* input_buffer = (uint8_t*)malloc(file_size);
    size_t output_size = cf_compress_bound(file_size);
    uint8_t* output_buffer = (uint8_t*)malloc(output_size);

    if (!input_buffer || !output_buffer) {
        free(input_buffer);
        free(output_buffer);
        fclose(in_file);
        fclose(out_file);
        return CF_ERROR_OUT_OF_MEMORY;
    }

    /* Read input file */
    if (fread(input_buffer, 1, file_size, in_file) != file_size) {
        free(input_buffer);
        free(output_buffer);
        fclose(in_file);
        fclose(out_file);
        return CF_ERROR_IO_FAILURE;
    }

    /* Compress */
    cf_error_t result = cf_compress(input_buffer, file_size,
                                    output_buffer, &output_size, level);

    if (result == CF_SUCCESS) {
        /* Write output */
        if (fwrite(output_buffer, 1, output_size, out_file) != output_size) {
            result = CF_ERROR_IO_FAILURE;
        }
    }

    /* Cleanup */
    free(input_buffer);
    free(output_buffer);
    fclose(in_file);
    fclose(out_file);

    return result;
}

cf_error_t cf_decompress_file(
    const char* input_path,
    const char* output_path
) {
    FILE* in_file = fopen(input_path, "rb");
    if (!in_file) return CF_ERROR_IO_FAILURE;

    FILE* out_file = fopen(output_path, "wb");
    if (!out_file) {
        fclose(in_file);
        return CF_ERROR_IO_FAILURE;
    }

    /* Get file size */
    fseek(in_file, 0, SEEK_END);
    size_t file_size = ftell(in_file);
    fseek(in_file, 0, SEEK_SET);

    /* Allocate buffers */
    uint8_t* input_buffer = (uint8_t*)malloc(file_size);
    /* Estimate decompressed size (can be improved with header info) */
    size_t output_size = file_size * 10;  /* Conservative estimate */
    uint8_t* output_buffer = (uint8_t*)malloc(output_size);

    if (!input_buffer || !output_buffer) {
        free(input_buffer);
        free(output_buffer);
        fclose(in_file);
        fclose(out_file);
        return CF_ERROR_OUT_OF_MEMORY;
    }

    /* Read input file */
    if (fread(input_buffer, 1, file_size, in_file) != file_size) {
        free(input_buffer);
        free(output_buffer);
        fclose(in_file);
        fclose(out_file);
        return CF_ERROR_IO_FAILURE;
    }

    /* Decompress */
    cf_error_t result = cf_decompress(input_buffer, file_size,
                                      output_buffer, &output_size);

    if (result == CF_SUCCESS) {
        /* Write output */
        if (fwrite(output_buffer, 1, output_size, out_file) != output_size) {
            result = CF_ERROR_IO_FAILURE;
        }
    }

    /* Cleanup */
    free(input_buffer);
    free(output_buffer);
    fclose(in_file);
    fclose(out_file);

    return result;
}