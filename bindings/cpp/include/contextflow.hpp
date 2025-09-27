/**
 * ContextFlow C++ Wrapper
 * Modern C++ interface for ContextFlow compression library
 * Version 4.0.0 - Q1 2025
 */

#ifndef CONTEXTFLOW_HPP
#define CONTEXTFLOW_HPP

#include <contextflow.h>
#include <memory>
#include <vector>
#include <string>
#include <stdexcept>
#include <functional>
#include <optional>
#include <filesystem>

namespace contextflow {

/**
 * Exception class for ContextFlow errors
 */
class Exception : public std::runtime_error {
public:
    explicit Exception(cf_error_t error)
        : std::runtime_error(cf_error_string(error)), error_code_(error) {}

    cf_error_t error_code() const { return error_code_; }

private:
    cf_error_t error_code_;
};

/**
 * RAII wrapper for compression statistics
 */
class Statistics {
public:
    Statistics() = default;
    explicit Statistics(const cf_stats_t& stats) : stats_(stats) {}

    uint64_t originalSize() const { return stats_.original_size; }
    uint64_t compressedSize() const { return stats_.compressed_size; }
    double compressionRatio() const { return stats_.compression_ratio; }
    double compressionSpeedMbps() const { return stats_.compression_speed_mbps; }
    double decompressionSpeedMbps() const { return stats_.decompression_speed_mbps; }
    uint64_t memoryUsed() const { return stats_.memory_used; }
    uint32_t checksum() const { return stats_.checksum; }

private:
    cf_stats_t stats_{};
};

/**
 * Compression mode enum class
 */
enum class Mode {
    Standard = CF_MODE_STANDARD,
    Turbo = CF_MODE_TURBO,
    Quantum = CF_MODE_QUANTUM,
    Streaming = CF_MODE_STREAMING,
    Delta = CF_MODE_DELTA,
    Dictionary = CF_MODE_DICTIONARY
};

/**
 * Compression level enum class
 */
enum class Level {
    Fastest = CF_LEVEL_FASTEST,
    Fast = CF_LEVEL_FAST,
    Default = CF_LEVEL_DEFAULT,
    Better = CF_LEVEL_BETTER,
    Best = CF_LEVEL_BEST
};

/**
 * Forward declarations
 */
class Compressor;
class Decompressor;
class StreamCompressor;
class DictionaryBuilder;

/**
 * Simple compression/decompression functions
 */
class Simple {
public:
    /**
     * Compress data with specified level
     * @param data Input data
     * @param level Compression level
     * @return Compressed data
     * @throws Exception on compression failure
     */
    static std::vector<uint8_t> compress(
        const std::vector<uint8_t>& data,
        Level level = Level::Default
    ) {
        size_t output_size = cf_compress_bound(data.size());
        std::vector<uint8_t> output(output_size);

        cf_error_t result = cf_compress(
            data.data(), data.size(),
            output.data(), &output_size,
            static_cast<cf_level_t>(level)
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        output.resize(output_size);
        return output;
    }

    /**
     * Decompress data
     * @param data Compressed data
     * @return Decompressed data
     * @throws Exception on decompression failure
     */
    static std::vector<uint8_t> decompress(const std::vector<uint8_t>& data) {
        // Initial size estimation (can be improved)
        size_t output_size = data.size() * 10;
        std::vector<uint8_t> output(output_size);

        cf_error_t result = cf_decompress(
            data.data(), data.size(),
            output.data(), &output_size
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        output.resize(output_size);
        return output;
    }

    /**
     * Compress string
     * @param str Input string
     * @param level Compression level
     * @return Compressed data
     */
    static std::vector<uint8_t> compressString(
        const std::string& str,
        Level level = Level::Default
    ) {
        std::vector<uint8_t> data(str.begin(), str.end());
        return compress(data, level);
    }

    /**
     * Decompress to string
     * @param data Compressed data
     * @return Decompressed string
     */
    static std::string decompressString(const std::vector<uint8_t>& data) {
        auto decompressed = decompress(data);
        return std::string(decompressed.begin(), decompressed.end());
    }
};

/**
 * Context wrapper for advanced compression
 */
class Context {
public:
    Context(Mode mode = Mode::Standard, Level level = Level::Default)
        : ctx_(cf_create_context(
            static_cast<cf_mode_t>(mode),
            static_cast<cf_level_t>(level)
        )) {
        if (!ctx_) {
            throw Exception(CF_ERROR_OUT_OF_MEMORY);
        }
    }

    ~Context() {
        if (ctx_) {
            cf_destroy_context(ctx_);
        }
    }

    // Delete copy constructor and assignment
    Context(const Context&) = delete;
    Context& operator=(const Context&) = delete;

    // Move semantics
    Context(Context&& other) noexcept : ctx_(other.ctx_) {
        other.ctx_ = nullptr;
    }

    Context& operator=(Context&& other) noexcept {
        if (this != &other) {
            if (ctx_) {
                cf_destroy_context(ctx_);
            }
            ctx_ = other.ctx_;
            other.ctx_ = nullptr;
        }
        return *this;
    }

    /**
     * Compress data
     * @param input Input data
     * @return Compressed data
     */
    std::vector<uint8_t> compress(const std::vector<uint8_t>& input) {
        size_t output_size = cf_compress_bound(input.size());
        std::vector<uint8_t> output(output_size);

        cf_error_t result = cf_compress_ctx(
            ctx_,
            input.data(), input.size(),
            output.data(), &output_size
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        output.resize(output_size);
        return output;
    }

    /**
     * Decompress data
     * @param input Compressed data
     * @return Decompressed data
     */
    std::vector<uint8_t> decompress(const std::vector<uint8_t>& input) {
        size_t output_size = input.size() * 10;  // Estimate
        std::vector<uint8_t> output(output_size);

        cf_error_t result = cf_decompress_ctx(
            ctx_,
            input.data(), input.size(),
            output.data(), &output_size
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        output.resize(output_size);
        return output;
    }

    /**
     * Reset context for reuse
     */
    void reset() {
        cf_error_t result = cf_reset_context(ctx_);
        if (result != CF_SUCCESS) {
            throw Exception(result);
        }
    }

    /**
     * Get compression statistics
     * @return Statistics object
     */
    Statistics getStatistics() const {
        cf_stats_t stats;
        cf_error_t result = cf_get_stats(ctx_, &stats);
        if (result != CF_SUCCESS) {
            throw Exception(result);
        }
        return Statistics(stats);
    }

    /**
     * Load dictionary
     * @param dictionary Dictionary data
     */
    void loadDictionary(const std::vector<uint8_t>& dictionary) {
        cf_error_t result = cf_load_dictionary(
            ctx_,
            dictionary.data(),
            dictionary.size()
        );
        if (result != CF_SUCCESS) {
            throw Exception(result);
        }
    }

    /**
     * Get raw context handle
     * @return Raw context pointer
     */
    cf_context_t* handle() const { return ctx_; }

private:
    cf_context_t* ctx_;
};

/**
 * Stream compression class
 */
class StreamCompressor {
public:
    using Callback = std::function<void(const std::vector<uint8_t>&)>;

    StreamCompressor(Mode mode = Mode::Streaming, Level level = Level::Default)
        : context_(mode, level) {}

    /**
     * Begin streaming compression
     */
    void begin() {
        cf_error_t result = cf_stream_begin(context_.handle());
        if (result != CF_SUCCESS) {
            throw Exception(result);
        }
    }

    /**
     * Process chunk
     * @param chunk Input chunk
     * @param finished Whether this is the last chunk
     * @return Compressed chunk
     */
    std::vector<uint8_t> process(
        const std::vector<uint8_t>& chunk,
        bool finished = false
    ) {
        size_t output_size = cf_compress_bound(chunk.size());
        std::vector<uint8_t> output(output_size);

        cf_error_t result = cf_stream_process(
            context_.handle(),
            chunk.data(), chunk.size(),
            output.data(), &output_size,
            finished
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        output.resize(output_size);
        return output;
    }

    /**
     * End streaming compression
     */
    void end() {
        cf_error_t result = cf_stream_end(context_.handle());
        if (result != CF_SUCCESS) {
            throw Exception(result);
        }
    }

    /**
     * Process stream with callback
     * @param input Input stream
     * @param callback Callback for compressed chunks
     * @param chunk_size Size of chunks to process
     */
    template<typename InputStream>
    void processStream(
        InputStream& input,
        Callback callback,
        size_t chunk_size = 65536
    ) {
        begin();

        std::vector<uint8_t> buffer(chunk_size);
        while (input.good()) {
            input.read(reinterpret_cast<char*>(buffer.data()), chunk_size);
            size_t bytes_read = input.gcount();

            if (bytes_read > 0) {
                buffer.resize(bytes_read);
                bool is_last = !input.good();
                auto compressed = process(buffer, is_last);
                callback(compressed);
            }
        }

        end();
    }

private:
    Context context_;
};

/**
 * Dictionary builder class
 */
class DictionaryBuilder {
public:
    /**
     * Add sample for dictionary training
     * @param sample Sample data
     */
    void addSample(const std::vector<uint8_t>& sample) {
        samples_.push_back(sample);
    }

    /**
     * Build dictionary from samples
     * @param max_size Maximum dictionary size
     * @return Built dictionary
     */
    std::vector<uint8_t> build(size_t max_size = 32768) {
        if (samples_.empty()) {
            throw std::runtime_error("No samples provided");
        }

        std::vector<const uint8_t*> sample_ptrs;
        std::vector<size_t> sample_sizes;

        for (const auto& sample : samples_) {
            sample_ptrs.push_back(sample.data());
            sample_sizes.push_back(sample.size());
        }

        std::vector<uint8_t> dictionary(max_size);
        size_t dict_size = max_size;

        cf_error_t result = cf_build_dictionary(
            sample_ptrs.data(),
            sample_sizes.data(),
            samples_.size(),
            dictionary.data(),
            &dict_size
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        dictionary.resize(dict_size);
        return dictionary;
    }

    /**
     * Clear samples
     */
    void clear() {
        samples_.clear();
    }

private:
    std::vector<std::vector<uint8_t>> samples_;
};

/**
 * Delta compression utilities
 */
class Delta {
public:
    /**
     * Compute delta between two versions
     * @param base Base version
     * @param target Target version
     * @return Delta data
     */
    static std::vector<uint8_t> compute(
        const std::vector<uint8_t>& base,
        const std::vector<uint8_t>& target
    ) {
        size_t delta_size = target.size() + base.size() / 2;  // Estimate
        std::vector<uint8_t> delta(delta_size);

        cf_error_t result = cf_compute_delta(
            base.data(), base.size(),
            target.data(), target.size(),
            delta.data(), &delta_size
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        delta.resize(delta_size);
        return delta;
    }

    /**
     * Apply delta to base version
     * @param base Base version
     * @param delta Delta data
     * @return Target version
     */
    static std::vector<uint8_t> apply(
        const std::vector<uint8_t>& base,
        const std::vector<uint8_t>& delta
    ) {
        size_t output_size = base.size() + delta.size() * 2;  // Estimate
        std::vector<uint8_t> output(output_size);

        cf_error_t result = cf_apply_delta(
            base.data(), base.size(),
            delta.data(), delta.size(),
            output.data(), &output_size
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }

        output.resize(output_size);
        return output;
    }
};

/**
 * File compression utilities
 */
class File {
public:
    /**
     * Compress file
     * @param input_path Input file path
     * @param output_path Output file path
     * @param level Compression level
     */
    static void compress(
        const std::filesystem::path& input_path,
        const std::filesystem::path& output_path,
        Level level = Level::Default
    ) {
        cf_error_t result = cf_compress_file(
            input_path.string().c_str(),
            output_path.string().c_str(),
            static_cast<cf_level_t>(level)
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }
    }

    /**
     * Decompress file
     * @param input_path Input file path
     * @param output_path Output file path
     */
    static void decompress(
        const std::filesystem::path& input_path,
        const std::filesystem::path& output_path
    ) {
        cf_error_t result = cf_decompress_file(
            input_path.string().c_str(),
            output_path.string().c_str()
        );

        if (result != CF_SUCCESS) {
            throw Exception(result);
        }
    }
};

/**
 * Initialize library (call once at startup)
 */
inline void initialize() {
    cf_error_t result = cf_init();
    if (result != CF_SUCCESS) {
        throw Exception(result);
    }
}

/**
 * Cleanup library (call once at shutdown)
 */
inline void cleanup() {
    cf_cleanup();
}

/**
 * Get library version
 */
inline std::string version() {
    return cf_version();
}

} // namespace contextflow

#endif // CONTEXTFLOW_HPP