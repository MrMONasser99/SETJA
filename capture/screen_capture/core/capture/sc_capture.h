#pragma once
#include <windows.h>
#include <atomic>
#include <mutex>
#include <thread>
#include <string>

namespace cap {
    struct Shared {
        std::atomic<bool> stop{false};
        std::mutex region_mu;
        RECT region{0,0,0,0};
        long long region_updates = 0;
    };

    void print_region_line(const RECT& reg, long long updates, double target_fps, const std::wstring& region_path);
    void capture_thread(Shared* sh, double target_fps);
}