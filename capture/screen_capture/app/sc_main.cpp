#define NOMINMAX
#include <windows.h>
#include <iostream>
#include <thread>
#include <chrono>

#include "../core/region/sc_region.h"
#include "../core/capture/sc_capture.h"

static cap::Shared* g_shared = nullptr;

static BOOL WINAPI console_ctrl_handler(DWORD type) {
    if (!g_shared) return FALSE;    
    if (type == CTRL_C_EVENT || type == CTRL_CLOSE_EVENT || type == CTRL_BREAK_EVENT) {
        g_shared->stop.store(true);
        return TRUE;
    }
    return FALSE;
}

int main() {
    const double target_fps = 15.0;
    const double ui_interval = 0.2;

    cap::Shared sh{};
    g_shared = &sh;
    SetConsoleCtrlHandler(console_ctrl_handler, TRUE);

    std::wstring region_path = region::default_region_path();

    int W = GetSystemMetrics(SM_CXSCREEN);
    int H = GetSystemMetrics(SM_CYSCREEN);

    RECT def{0,0,W,H};

    {
        std::lock_guard<std::mutex> lk(sh.region_mu);
        sh.region = def;
        sh.region_updates = 1;
    }
    
    FILETIME last_mtime{};
    bool has_mtime = region::file_mtime(region_path, last_mtime);

    RECT rfile{};
    if (region::read_from_json(region_path, rfile)) {
        std::lock_guard<std::mutex> lk(sh.region_mu);
        sh.region = rfile;
        sh.region_updates++;
        cap::print_region_line(sh.region, sh.region_updates, target_fps, region_path);
    }

    std::thread capthr(cap::capture_thread, &sh, target_fps);

    while (!sh.stop.load()) {
        std::this_thread::sleep_for(std::chrono::duration<double>(ui_interval));

        if (GetAsyncKeyState(VK_ESCAPE) & 0x8000) {
            sh.stop.store(true);
            break;
        }

        FILETIME mt{};
        bool okm = region::file_mtime(region_path, mt);
        if (okm && (!has_mtime || CompareFileTime(&mt, &last_mtime) != 0)) {
            RECT nr{};
            if (region::read_from_json(region_path, nr)) {
                std::lock_guard<std::mutex> lk(sh.region_mu);
                sh.region = nr;
                sh.region_updates++;
                cap::print_region_line(sh.region, sh.region_updates, target_fps, region_path);
            }
            last_mtime = mt;
            has_mtime = true;
        }
    }

    sh.stop.store(true);
    if (capthr.joinable()) capthr.join();
    return 0;
}
