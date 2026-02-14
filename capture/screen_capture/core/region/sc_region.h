#pragma once
#include <windows.h>
#include <string>

namespace region {
    bool read_from_json(const std::wstring& path, RECT& outLTRB);
    bool file_mtime(const std::wstring& path, FILETIME& ft);
    std::wstring default_region_path();
}
