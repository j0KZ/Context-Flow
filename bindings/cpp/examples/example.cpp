/**
 * ContextFlow C++ Example
 * Demonstrates modern C++ API usage
 */

#include <contextflow.hpp>
#include <iostream>
#include <chrono>
#include <fstream>
#include <iomanip>

using namespace contextflow;
using namespace std::chrono;

void printVector(const std::vector<uint8_t>& vec, size_t max_len = 50) {
    std::cout << "Data (first " << std::min(vec.size(), max_len) << " bytes): ";
    for (size_t i = 0; i < std::min(vec.size(), max_len); ++i) {
        std::cout << std::hex << std::setw(2) << std::setfill('0')
                  << static_cast<int>(vec[i]) << " ";
    }
    if (vec.size() > max_len) {
        std::cout << "...";
    }
    std::cout << std::dec << std::endl;
}

int main() {
    try {
        std::cout << "ContextFlow C++ Example - Version " << version() << "\n\n";

        // Example 1: Simple compression
        std::cout << "Example 1: Simple Compression\n";
        std::cout << "=============================\n";

        std::string text = "The quick brown fox jumps over the lazy dog. "
                           "The quick brown fox jumps over the lazy dog. "
                           "The quick brown fox jumps over the lazy dog. "
                           "The quick brown fox jumps over the lazy dog. ";

        auto start = high_resolution_clock::now();
        auto compressed = Simple::compressString(text, Level::Default);
        auto end = high_resolution_clock::now();

        auto duration = duration_cast<microseconds>(end - start);
        double ratio = static_cast<double>(text.size()) / compressed.size();

        std::cout << "Original size: " << text.size() << " bytes\n";
        std::cout << "Compressed size: " << compressed.size() << " bytes\n";
        std::cout << "Compression ratio: " << std::fixed << std::setprecision(2)
                  << ratio << "x\n";
        std::cout << "Time taken: " << duration.count() << " μs\n";

        // Decompress and verify
        auto decompressed = Simple::decompressString(compressed);
        if (decompressed == text) {
            std::cout << "Decompression successful - data verified!\n";
        } else {
            std::cout << "Decompression failed - data mismatch!\n";
        }

        std::cout << "\n";

        // Example 2: Context-based compression with different modes
        std::cout << "Example 2: Different Compression Modes\n";
        std::cout << "======================================\n";

        std::vector<std::pair<Mode, std::string>> modes = {
            {Mode::Standard, "Standard"},
            {Mode::Turbo, "Turbo"},
            {Mode::Quantum, "Quantum"}
        };

        std::vector<uint8_t> data(text.begin(), text.end());

        for (const auto& [mode, name] : modes) {
            Context ctx(mode, Level::Default);

            start = high_resolution_clock::now();
            auto compressed_ctx = ctx.compress(data);
            end = high_resolution_clock::now();

            duration = duration_cast<microseconds>(end - start);
            auto stats = ctx.getStatistics();

            std::cout << "\n" << name << " mode:\n";
            std::cout << "  Compressed size: " << compressed_ctx.size() << " bytes\n";
            std::cout << "  Compression ratio: " << std::fixed << std::setprecision(2)
                      << static_cast<double>(data.size()) / compressed_ctx.size() << "x\n";
            std::cout << "  Time taken: " << duration.count() << " μs\n";
        }

        std::cout << "\n";

        // Example 3: Streaming compression
        std::cout << "Example 3: Streaming Compression\n";
        std::cout << "================================\n";

        StreamCompressor streamer(Mode::Streaming, Level::Default);
        std::vector<std::vector<uint8_t>> compressed_chunks;

        // Simulate streaming with string stream
        std::istringstream stream(text);
        size_t total_compressed = 0;

        streamer.processStream(stream, [&](const std::vector<uint8_t>& chunk) {
            compressed_chunks.push_back(chunk);
            total_compressed += chunk.size();
            std::cout << "  Processed chunk: " << chunk.size() << " bytes\n";
        }, 64);  // 64-byte chunks

        std::cout << "Streaming compression completed\n";
        std::cout << "Total chunks: " << compressed_chunks.size() << "\n";
        std::cout << "Total compressed size: " << total_compressed << " bytes\n";
        std::cout << "Compression ratio: " << std::fixed << std::setprecision(2)
                  << static_cast<double>(text.size()) / total_compressed << "x\n";

        std::cout << "\n";

        // Example 4: Dictionary compression
        std::cout << "Example 4: Dictionary Compression\n";
        std::cout << "==================================\n";

        DictionaryBuilder builder;

        // Add samples for dictionary training
        std::vector<std::string> samples = {
            "The quick brown fox jumps over the lazy dog.",
            "The quick brown fox runs quickly.",
            "The lazy dog sleeps under the tree.",
            "A quick brown fox is a fast animal."
        };

        for (const auto& sample : samples) {
            std::vector<uint8_t> sample_data(sample.begin(), sample.end());
            builder.addSample(sample_data);
        }

        auto dictionary = builder.build(1024);  // 1KB dictionary
        std::cout << "Dictionary built: " << dictionary.size() << " bytes\n";

        // Use dictionary for compression
        Context dict_ctx(Mode::Dictionary, Level::Default);
        dict_ctx.loadDictionary(dictionary);

        std::string new_text = "The quick brown fox jumps very quickly.";
        std::vector<uint8_t> new_data(new_text.begin(), new_text.end());

        auto dict_compressed = dict_ctx.compress(new_data);
        auto normal_compressed = Simple::compress(new_data);

        std::cout << "Text: \"" << new_text << "\"\n";
        std::cout << "Normal compressed size: " << normal_compressed.size() << " bytes\n";
        std::cout << "Dictionary compressed size: " << dict_compressed.size() << " bytes\n";
        std::cout << "Improvement: "
                  << (1.0 - static_cast<double>(dict_compressed.size()) / normal_compressed.size()) * 100
                  << "%\n";

        std::cout << "\n";

        // Example 5: Delta compression
        std::cout << "Example 5: Delta Compression\n";
        std::cout << "============================\n";

        std::string version1 = "The quick brown fox jumps over the lazy dog.";
        std::string version2 = "The quick brown fox runs over the lazy cat.";

        std::vector<uint8_t> v1(version1.begin(), version1.end());
        std::vector<uint8_t> v2(version2.begin(), version2.end());

        auto delta = Delta::compute(v1, v2);

        std::cout << "Version 1: \"" << version1 << "\" (" << v1.size() << " bytes)\n";
        std::cout << "Version 2: \"" << version2 << "\" (" << v2.size() << " bytes)\n";
        std::cout << "Delta size: " << delta.size() << " bytes\n";
        std::cout << "Space saved: " << (v2.size() - delta.size()) << " bytes ("
                  << (1.0 - static_cast<double>(delta.size()) / v2.size()) * 100 << "%)\n";

        // Apply delta to reconstruct version2
        auto reconstructed = Delta::apply(v1, delta);
        std::string reconstructed_str(reconstructed.begin(), reconstructed.end());

        if (reconstructed_str == version2) {
            std::cout << "Delta successfully applied - version 2 reconstructed!\n";
        }

        std::cout << "\n";

        // Example 6: File compression (if files exist)
        std::cout << "Example 6: File Compression\n";
        std::cout << "===========================\n";

        // Create a test file
        std::string test_filename = "test_input.txt";
        std::string compressed_filename = "test_input.ctx";
        std::string decompressed_filename = "test_output.txt";

        std::ofstream test_file(test_filename);
        test_file << text;
        test_file.close();

        try {
            File::compress(test_filename, compressed_filename, Level::Best);
            std::cout << "File compressed: " << test_filename << " -> "
                      << compressed_filename << "\n";

            File::decompress(compressed_filename, decompressed_filename);
            std::cout << "File decompressed: " << compressed_filename << " -> "
                      << decompressed_filename << "\n";

            // Verify content
            std::ifstream original(test_filename);
            std::ifstream restored(decompressed_filename);
            std::string original_content((std::istreambuf_iterator<char>(original)),
                                         std::istreambuf_iterator<char>());
            std::string restored_content((std::istreambuf_iterator<char>(restored)),
                                         std::istreambuf_iterator<char>());

            if (original_content == restored_content) {
                std::cout << "File compression/decompression verified!\n";
            }

            // Clean up test files
            std::filesystem::remove(test_filename);
            std::filesystem::remove(compressed_filename);
            std::filesystem::remove(decompressed_filename);

        } catch (const Exception& e) {
            std::cout << "File operation failed: " << e.what() << "\n";
        }

        std::cout << "\nAll examples completed successfully!\n";

    } catch (const Exception& e) {
        std::cerr << "ContextFlow error: " << e.what() << "\n";
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}