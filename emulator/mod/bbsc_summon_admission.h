#pragma once

#include <atomic>
#include <optional>
#include <string>
#include <string_view>

namespace BbscMod {

// HTTP events are serialized by the wrapper's request mutex. The native
// selector only reads blocked_, without taking that mutex on the game thread.
class SummonAdmission {
public:
    bool Blocked() const { return blocked_.load(); }

    void BeginClaim(int request) {
        if (!supported_) return;
        claim_ = request;
        search_.reset();
        blocked_ = true;
    }

    void BeginSearch(int request) {
        if (claim_) return;
        search_ = request;
        prefix_.clear();
    }

    void Read(int request, std::string_view chunk) {
        if (search_ != request) return;
        // Party serializes JSON with sorted keys. Read only the leading flag,
        // which can arrive across several sceHttpReadData calls.
        constexpr std::string_view key = "{\"BBSCAdmissionReady\":";
        prefix_.append(chunk.substr(0, key.size() + 2 - prefix_.size()));
        if (!key.starts_with(std::string_view(prefix_).substr(0, key.size()))) {
            search_.reset();
            return;
        }
        if (prefix_.size() < key.size() + 2) return;
        search_.reset();
        const char ready = prefix_[key.size()];
        if ((ready == '0' || ready == '1') && prefix_.back() == ',') {
            supported_ = true;
            blocked_ = ready == '0';
        }
    }

    void Finish(int request) {
        if (claim_ == request) claim_.reset();
        if (search_ == request) search_.reset();
    }

private:
    std::atomic<bool> blocked_{false};
    bool supported_ = false;
    std::optional<int> claim_;
    std::optional<int> search_;
    std::string prefix_;
};

bool PartySummonSelectionBlocked();

} // namespace BbscMod
