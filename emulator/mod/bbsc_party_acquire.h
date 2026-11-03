// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
#include <cstdint>

namespace BbscMod {
// One nonblocking request from the game thread to the maintenance worker.
// Generation and result share one CAS: a late HTTP answer cannot revive a cancel.
class PartyAcquireMailbox {
public:
    enum Result : std::uint64_t { Idle, Queued, Working, Granted, Denied, Stale };
    std::uint64_t Request() {
        auto old = value.load(std::memory_order_acquire);
        for (;;) {
            const auto state = old & Mask;
            if (state == Queued || state == Working || state == Granted) return old & ~Mask;
            const auto next = ((old & ~Mask) + Step) | Queued;
            if (value.compare_exchange_weak(old, next)) return next & ~Mask;
        }
    }
    std::uint64_t Take() {
        auto old = value.load(std::memory_order_acquire);
        if ((old & Mask) != Queued) return 0;
        return value.compare_exchange_strong(old, (old & ~Mask) | Working) ? old & ~Mask : 0;
    }
    bool Complete(std::uint64_t ticket, bool granted) {
        auto expected = ticket | Working;
        return value.compare_exchange_strong(expected, ticket | (granted ? Granted : Denied));
    }
    Result Poll(std::uint64_t ticket) const {
        const auto now = value.load(std::memory_order_acquire);
        return ticket && (now & ~Mask) == ticket ? Result(now & Mask) : Stale;
    }
    void Finish(std::uint64_t ticket) {
        auto old = value.load(std::memory_order_acquire);
        while ((old & ~Mask) == ticket && !value.compare_exchange_weak(old, ticket | Idle)) {}
    }
    void Cancel() {
        auto old = value.load(std::memory_order_acquire);
        while (!value.compare_exchange_weak(old, ((old & ~Mask) + Step) | Idle)) {}
    }
private:
    static constexpr std::uint64_t Mask = 7, Step = 8;
    std::atomic<std::uint64_t> value{Idle};
};
}
