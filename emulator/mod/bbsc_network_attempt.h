#pragma once
#include <atomic>
#include <cstdint>
namespace BbscMod {
// Callers serialize lifecycle observations; transport reads only the atomic serial.
struct NetworkAttemptTrace {
    std::atomic<std::uint64_t> serial{0};
    int previous_state = -1;
    void Claim() { serial.fetch_add(1, std::memory_order_relaxed); }
    bool State(int state, bool pending_claim) {
        if (state < 0) return false; // temporarily unreadable manager during a load
        const bool begin = (state == 4 || state == 6) && previous_state != 4 && previous_state != 6 && !pending_claim;
        previous_state = state;
        if (begin) Claim();
        return begin;
    }
};
}
