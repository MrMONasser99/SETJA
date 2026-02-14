#pragma once
#include <windows.h>
#include <cstdint>
#include <cstring>

namespace shm {
    extern const wchar_t* NAME;

    #pragma pack(push, 1)
    struct Header {
        uint32_t magic;
        uint32_t version;
        LONG seq;
        int32_t width;
        int32_t height;
        int32_t stride;
        int32_t format;
        int32_t region_left;
        int32_t region_top;
        uint32_t data_bytes;
    };
    #pragma pack(pop)

    extern const uint32_t MAGIC;
    extern const int32_t  FMT_BGRA8;

    struct Writer {
        HANDLE hMap = nullptr;
        uint8_t* base = nullptr;
        size_t size = 0;

        bool open_or_create(size_t bytes);
        void close();
        ~Writer();
    };
}