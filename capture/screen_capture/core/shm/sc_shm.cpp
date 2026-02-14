#include "sc_shm.h"

namespace shm {
    const wchar_t* NAME = L"Local\\SETJA_OCR_FRAME_V1";
    const uint32_t MAGIC = 0x4D464A53;
    const int32_t  FMT_BGRA8 = 1;

    bool Writer::open_or_create(size_t bytes) {
        if (hMap && base && size == bytes) return true;
        close();

        hMap = CreateFileMappingW(
            INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE,
            (DWORD)((bytes >> 32) & 0xFFFFFFFF),
            (DWORD)(bytes & 0xFFFFFFFF),
            NAME
        );
        if (!hMap) return false;

        DWORD le = GetLastError();
        const bool is_new = (le != ERROR_ALREADY_EXISTS);

        base = (uint8_t*)MapViewOfFile(hMap, FILE_MAP_ALL_ACCESS, 0, 0, bytes);
        if (!base) { CloseHandle(hMap); hMap = nullptr; return false; }

        if (is_new) std::memset(base, 0, bytes);

        size = bytes;
        return true;
    }

    void Writer::close() {
        if (base) UnmapViewOfFile(base);
        if (hMap) CloseHandle(hMap);
        base = nullptr;
        hMap = nullptr;
        size = 0;
    }

    Writer::~Writer() { close(); }
}