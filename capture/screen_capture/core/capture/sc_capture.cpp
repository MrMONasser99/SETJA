#include "sc_capture.h"
#include "../shm/sc_shm.h"

#include <d3d11.h>
#include <dxgi1_2.h>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <algorithm>
#include <chrono>
#include <thread>

#include <atomic>
static std::atomic<bool> g_screen_ready_once{false};

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")

namespace cap {

    struct DxgiCap {
        ID3D11Device* dev = nullptr;
        ID3D11DeviceContext* ctx = nullptr;
        IDXGIOutputDuplication* dupl = nullptr;
        UINT deskW = 0, deskH = 0;

        bool init() {
            HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0,
                nullptr, 0, D3D11_SDK_VERSION, &dev, nullptr, &ctx);
            if (FAILED(hr)) return false;

            IDXGIDevice* dxgiDev = nullptr;
            hr = dev->QueryInterface(__uuidof(IDXGIDevice), (void**)&dxgiDev);
            if (FAILED(hr)) return false;

            IDXGIAdapter* adapter = nullptr;
            dxgiDev->GetAdapter(&adapter);
            dxgiDev->Release();

            IDXGIOutput* output = nullptr;
            adapter->EnumOutputs(0, &output);
            adapter->Release();

            IDXGIOutput1* out1 = nullptr;
            hr = output->QueryInterface(__uuidof(IDXGIOutput1), (void**)&out1);
            output->Release();
            if (FAILED(hr)) return false;

            hr = out1->DuplicateOutput(dev, &dupl);
            out1->Release();
            if (FAILED(hr)) return false;

            DXGI_OUTDUPL_DESC desc{};
            dupl->GetDesc(&desc);
            deskW = desc.ModeDesc.Width;
            deskH = desc.ModeDesc.Height;
            return true;
        }

        void shutdown() {
            if (dupl) dupl->Release();
            if (ctx) ctx->Release();
            if (dev) dev->Release();
            dupl = nullptr; ctx = nullptr; dev = nullptr;
        }
    };

    static void clamp_region_to_desktop(RECT& r, UINT W, UINT H) {
        if (r.left < 0) r.left = 0;
        if (r.top < 0) r.top = 0;
        if (r.right > (LONG)W) r.right = (LONG)W;
        if (r.bottom > (LONG)H) r.bottom = (LONG)H;
        if (r.right <= r.left) r.right = r.left + 1;
        if (r.bottom <= r.top) r.bottom = r.top + 1;
    }

    static ID3D11Texture2D* make_staging(ID3D11Device* dev, int w, int h) {
        if (w <= 0 || h <= 0) return nullptr;
        D3D11_TEXTURE2D_DESC td{};
        td.Width = (UINT)w;
        td.Height = (UINT)h;
        td.MipLevels = 1;
        td.ArraySize = 1;
        td.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        td.SampleDesc.Count = 1;
        td.Usage = D3D11_USAGE_STAGING;
        td.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        ID3D11Texture2D* tex = nullptr;
        if (FAILED(dev->CreateTexture2D(&td, nullptr, &tex))) return nullptr;
        return tex;
    }

    void print_region_line(const RECT&, long long, double, const std::wstring&) {
    }

    void capture_thread(Shared* sh, double target_fps) {
        DxgiCap capdev;
        if (!capdev.init()) return;

        ID3D11Texture2D* staging = nullptr;
        int stW = 0, stH = 0;
        long long last_updates = -1;

        shm::Writer shmw;

        const double min_dt = (target_fps > 0 ? (1.0 / target_fps) : 0.0);
        auto next_t = std::chrono::high_resolution_clock::now();

        while (!sh->stop.load()) {
            RECT r;
            long long upd;
            {
                std::lock_guard<std::mutex> lk(sh->region_mu);
                r = sh->region;
                upd = sh->region_updates;
            }

            clamp_region_to_desktop(r, capdev.deskW, capdev.deskH);
            const int w = r.right - r.left;
            const int h = r.bottom - r.top;

            if (!staging || w != stW || h != stH || upd != last_updates) {
                if (staging) staging->Release();
                staging = make_staging(capdev.dev, w, h);
                stW = w; stH = h;
                last_updates = upd;
            }

            IDXGIResource* res = nullptr;
            DXGI_OUTDUPL_FRAME_INFO info{};
            DWORD timeout_ms = (target_fps > 0)
                ? static_cast<DWORD>((std::max)(1.0, 1000.0 / target_fps))
                : 0;

            HRESULT hr = capdev.dupl->AcquireNextFrame(timeout_ms, &info, &res);

            if (hr == DXGI_ERROR_WAIT_TIMEOUT) {
            } else if (SUCCEEDED(hr)) {
                ID3D11Texture2D* frame = nullptr;
                res->QueryInterface(__uuidof(ID3D11Texture2D), (void**)&frame);
                res->Release();

                if (frame && staging) {
                    D3D11_BOX box{};
                    box.left = (UINT)r.left;
                    box.top = (UINT)r.top;
                    box.front = 0;
                    box.right = (UINT)r.right;
                    box.bottom = (UINT)r.bottom;
                    box.back = 1;

                    capdev.ctx->CopySubresourceRegion(staging, 0, 0, 0, 0, frame, 0, &box);

                    D3D11_MAPPED_SUBRESOURCE map{};
                    if (SUCCEEDED(capdev.ctx->Map(staging, 0, D3D11_MAP_READ, 0, &map))) {
                        const int shm_stride = w * 4;
                        const uint32_t data_bytes = (uint32_t)(h * shm_stride);
                        const size_t total_bytes = sizeof(shm::Header) + (size_t)data_bytes;

                        if (shmw.open_or_create(total_bytes)) {
                            auto* hdr = (shm::Header*)shmw.base;
                            uint8_t* dst = shmw.base + sizeof(shm::Header);

                            InterlockedIncrement(&hdr->seq);

                            hdr->magic = shm::MAGIC;
                            hdr->version = 1;
                            hdr->width = w;
                            hdr->height = h;
                            hdr->stride = shm_stride;
                            hdr->format = shm::FMT_BGRA8;
                            hdr->region_left = r.left;
                            hdr->region_top  = r.top;
                            hdr->data_bytes  = data_bytes;

                            const uint8_t* src = (const uint8_t*)map.pData;
                            const int src_pitch = (int)map.RowPitch;

                            for (int yy = 0; yy < h; yy++) {
                                const uint8_t* srow = src + (size_t)yy * (size_t)src_pitch;
                                uint8_t* drow = dst + (size_t)yy * (size_t)shm_stride;
                                std::memcpy(drow, srow, (size_t)shm_stride);
                            }

                            if (!g_screen_ready_once.exchange(true)) {
                                std::cout << "Screen Capture Running Successfully\n";
                            }                           

                            InterlockedIncrement(&hdr->seq);
                        }

                        capdev.ctx->Unmap(staging, 0);
                    }
                }

                if (frame) frame->Release();
                capdev.dupl->ReleaseFrame();
            } else if (hr == DXGI_ERROR_ACCESS_LOST) {
                capdev.shutdown();
                if (!capdev.init()) break;
            }

            if (min_dt > 0) {
                next_t += std::chrono::duration_cast<std::chrono::high_resolution_clock::duration>(
                    std::chrono::duration<double>(min_dt)
                );
                auto sleep_d = next_t - std::chrono::high_resolution_clock::now();
                if (sleep_d > std::chrono::high_resolution_clock::duration::zero()) {
                    std::this_thread::sleep_for(sleep_d);
                } else {
                    next_t = std::chrono::high_resolution_clock::now();
                }
            }
        }

        if (staging) staging->Release();
        capdev.shutdown();
    }

}