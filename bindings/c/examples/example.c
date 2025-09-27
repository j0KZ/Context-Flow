/**
 * ContextFlow C Library Example
 * Demonstrates basic compression and decompression
 */

#include <contextflow.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

void print_statistics(const cf_stats_t* stats) {
    printf("Statistics:\n");
    printf("  Original size: %llu bytes\n", (unsigned long long)stats->original_size);
    printf("  Compressed size: %llu bytes\n", (unsigned long long)stats->compressed_size);
    printf("  Compression ratio: %.2fx\n", stats->compression_ratio);
    printf("  Memory used: %llu bytes\n", (unsigned long long)stats->memory_used);
}

int main() {
    printf("ContextFlow C Example - Version %s\n\n", cf_version());

    // Initialize library
    cf_error_t result = cf_init();
    if (result != CF_SUCCESS) {
        fprintf(stderr, "Failed to initialize library: %s\n", cf_error_string(result));
        return 1;
    }

    // Example 1: Simple compression
    printf("Example 1: Simple Compression\n");
    printf("=============================\n");

    const char* text = "The quick brown fox jumps over the lazy dog. "
                       "The quick brown fox jumps over the lazy dog. "
                       "The quick brown fox jumps over the lazy dog. "
                       "The quick brown fox jumps over the lazy dog. ";

    size_t input_size = strlen(text);
    size_t compressed_size = cf_compress_bound(input_size);
    uint8_t* compressed = (uint8_t*)malloc(compressed_size);

    clock_t start = clock();
    result = cf_compress(
        (const uint8_t*)text, input_size,
        compressed, &compressed_size,
        CF_LEVEL_DEFAULT
    );
    clock_t end = clock();

    if (result == CF_SUCCESS) {
        double time_taken = ((double)(end - start)) / CLOCKS_PER_SEC;
        double ratio = (double)input_size / compressed_size;

        printf("Original size: %zu bytes\n", input_size);
        printf("Compressed size: %zu bytes\n", compressed_size);
        printf("Compression ratio: %.2fx\n", ratio);
        printf("Time taken: %.4f seconds\n", time_taken);

        // Decompress to verify
        size_t decompressed_size = input_size * 2;  // Safe margin
        uint8_t* decompressed = (uint8_t*)malloc(decompressed_size);

        result = cf_decompress(
            compressed, compressed_size,
            decompressed, &decompressed_size
        );

        if (result == CF_SUCCESS) {
            if (decompressed_size == input_size &&
                memcmp(text, decompressed, input_size) == 0) {
                printf("Decompression successful - data verified!\n");
            } else {
                printf("Decompression failed - data mismatch!\n");
            }
        } else {
            printf("Decompression failed: %s\n", cf_error_string(result));
        }

        free(decompressed);
    } else {
        printf("Compression failed: %s\n", cf_error_string(result));
    }

    free(compressed);
    printf("\n");

    // Example 2: Context-based compression with different modes
    printf("Example 2: Different Compression Modes\n");
    printf("======================================\n");

    cf_mode_t modes[] = {CF_MODE_STANDARD, CF_MODE_TURBO, CF_MODE_QUANTUM};
    const char* mode_names[] = {"Standard", "Turbo", "Quantum"};

    for (int i = 0; i < 3; i++) {
        cf_context_t* ctx = cf_create_context(modes[i], CF_LEVEL_DEFAULT);
        if (!ctx) {
            printf("Failed to create context for %s mode\n", mode_names[i]);
            continue;
        }

        compressed_size = cf_compress_bound(input_size);
        compressed = (uint8_t*)malloc(compressed_size);

        start = clock();
        result = cf_compress_ctx(
            ctx,
            (const uint8_t*)text, input_size,
            compressed, &compressed_size
        );
        end = clock();

        if (result == CF_SUCCESS) {
            cf_stats_t stats;
            cf_get_stats(ctx, &stats);

            double time_taken = ((double)(end - start)) / CLOCKS_PER_SEC;
            printf("\n%s mode:\n", mode_names[i]);
            printf("  Compressed size: %zu bytes\n", compressed_size);
            printf("  Compression ratio: %.2fx\n", (double)input_size / compressed_size);
            printf("  Time taken: %.4f seconds\n", time_taken);
        }

        free(compressed);
        cf_destroy_context(ctx);
    }

    printf("\n");

    // Example 3: Streaming compression
    printf("Example 3: Streaming Compression\n");
    printf("================================\n");

    cf_context_t* stream_ctx = cf_create_context(CF_MODE_STREAMING, CF_LEVEL_DEFAULT);
    if (stream_ctx) {
        cf_stream_begin(stream_ctx);

        // Process in chunks
        const size_t chunk_size = 64;
        size_t total_compressed = 0;

        for (size_t offset = 0; offset < input_size; offset += chunk_size) {
            size_t current_chunk = chunk_size;
            if (offset + current_chunk > input_size) {
                current_chunk = input_size - offset;
            }

            bool is_last = (offset + current_chunk >= input_size);

            compressed_size = cf_compress_bound(current_chunk);
            compressed = (uint8_t*)malloc(compressed_size);

            result = cf_stream_process(
                stream_ctx,
                (const uint8_t*)text + offset, current_chunk,
                compressed, &compressed_size,
                is_last
            );

            if (result == CF_SUCCESS) {
                total_compressed += compressed_size;
            }

            free(compressed);
        }

        cf_stream_end(stream_ctx);

        printf("Streaming compression completed\n");
        printf("Total compressed size: %zu bytes\n", total_compressed);
        printf("Compression ratio: %.2fx\n", (double)input_size / total_compressed);

        cf_destroy_context(stream_ctx);
    }

    printf("\n");

    // Example 4: Delta compression
    printf("Example 4: Delta Compression\n");
    printf("============================\n");

    const char* version1 = "The quick brown fox jumps over the lazy dog.";
    const char* version2 = "The quick brown fox runs over the lazy cat.";

    size_t v1_size = strlen(version1);
    size_t v2_size = strlen(version2);
    size_t delta_size = v1_size + v2_size;
    uint8_t* delta = (uint8_t*)malloc(delta_size);

    result = cf_compute_delta(
        (const uint8_t*)version1, v1_size,
        (const uint8_t*)version2, v2_size,
        delta, &delta_size
    );

    if (result == CF_SUCCESS) {
        printf("Version 1 size: %zu bytes\n", v1_size);
        printf("Version 2 size: %zu bytes\n", v2_size);
        printf("Delta size: %zu bytes\n", delta_size);
        printf("Space saved: %zu bytes (%.1f%%)\n",
               v2_size - delta_size,
               (1.0 - (double)delta_size / v2_size) * 100);

        // Apply delta to reconstruct version2
        size_t reconstructed_size = v2_size * 2;
        uint8_t* reconstructed = (uint8_t*)malloc(reconstructed_size);

        result = cf_apply_delta(
            (const uint8_t*)version1, v1_size,
            delta, delta_size,
            reconstructed, &reconstructed_size
        );

        if (result == CF_SUCCESS) {
            if (reconstructed_size == v2_size &&
                memcmp(version2, reconstructed, v2_size) == 0) {
                printf("Delta successfully applied - version 2 reconstructed!\n");
            }
        }

        free(reconstructed);
    }

    free(delta);
    printf("\n");

    // Cleanup
    cf_cleanup();

    printf("All examples completed!\n");
    return 0;
}