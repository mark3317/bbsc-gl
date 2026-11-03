// BBSC uses the native process stderr, captured by BBGL in last_run.log.
#pragma once
#include <cstdlib>
#include <cstring>
#include <string>
#include <fmt/format.h>

namespace BbscMod {
inline bool DiagnosticsEnabled() {
    static const bool enabled = [] {
        const char* value = std::getenv("BB_DIAGNOSTICS");
        return value && std::strcmp(value, "1") == 0;
    }();
    return enabled;
}
inline bool ShouldLog(char level) {
    static const int threshold = [] {
        const char* value = std::getenv("BBSC_LOG");
        const char* names[] = {"trace", "debug", "info", "warning", "error", "critical", "off"};
        if (value) for (int n = 0; n < 7; ++n) if (std::strcmp(value, names[n]) == 0) return n;
        return DiagnosticsEnabled() ? 0 : 4;
    }();
    const char* levels = "TDIWEC";
    const char* found = std::strchr(levels, level);
    return found && found - levels >= threshold;
}
void LogLine(char level, const char* category, const std::string& text);
}

#define BBSC_LOG(level, cat, ...) do { if (::BbscMod::ShouldLog(level)) \
    ::BbscMod::LogLine(level, #cat, fmt::format(__VA_ARGS__)); } while (false)
#define LOG_TRACE(cat, ...) BBSC_LOG('T', cat, __VA_ARGS__)
#define LOG_DEBUG(cat, ...) BBSC_LOG('D', cat, __VA_ARGS__)
#define LOG_INFO(cat, ...) BBSC_LOG('I', cat, __VA_ARGS__)
#define LOG_WARNING(cat, ...) BBSC_LOG('W', cat, __VA_ARGS__)
#define LOG_ERROR(cat, ...) BBSC_LOG('E', cat, __VA_ARGS__)
#define LOG_CRITICAL(cat, ...) BBSC_LOG('C', cat, __VA_ARGS__)
