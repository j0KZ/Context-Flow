/**
 * ContextFlow C++ Wrapper Implementation
 * Version 4.0.0 - Q1 2025
 */

#include "contextflow.hpp"

namespace contextflow {

// Static initialization
static bool g_initialized = false;

// Auto-initialization helper
class AutoInitializer {
public:
    AutoInitializer() {
        if (!g_initialized) {
            cf_init();
            g_initialized = true;
        }
    }

    ~AutoInitializer() {
        if (g_initialized) {
            cf_cleanup();
            g_initialized = false;
        }
    }
};

// Global initializer (ensures library is initialized)
static AutoInitializer g_auto_initializer;

} // namespace contextflow