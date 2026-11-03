#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
namespace BbscMod::RelayIo {
struct Attempt { int bytes; int error; bool blocked; };
struct Result { std::size_t bytes; int error; bool timeout; };
// One absolute deadline across partial sends and readiness waits. Unlike a
// per-send socket timeout, intermittent progress cannot extend it forever.
template<class Now, class Send, class Wait, class Progress>
Result SendFrame(const char* data, std::size_t size, Now now, Send send,
                 Wait wait, Progress progress, std::uint64_t timeout_ms = 10000) {
    const auto start = now();
    std::size_t offset = 0;
    while (offset < size) {
        const auto elapsed = now() - start;
        if (elapsed >= timeout_ms) return {offset, 0, true};
        const Attempt step = send(data + offset, static_cast<int>(size - offset));
        if (step.bytes > 0) {
            offset += step.bytes;
            progress(step.bytes);
        } else if (step.blocked) {
            const int error = wait(static_cast<int>(std::min<std::uint64_t>(250, timeout_ms - elapsed)));
            if (error) return {offset, error, false};
        } else {
            return {offset, step.error, false};
        }
    }
    return {offset, 0, false};
}
}
