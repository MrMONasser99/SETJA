#include "sc_region.h"

#include <fstream>
#include <vector>

namespace region {

    static std::string read_text_file_utf8(const std::wstring& path) {
        std::ifstream f(path, std::ios::binary);
        if (!f) return {};
        std::vector<char> buf((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
        return std::string(buf.begin(), buf.end());
    }

    static bool extract_int_key(const std::string& s, const char* key, int& out) {
        std::string k = "\"";
        k += key;
        k += "\"";
        size_t p = s.find(k);
        if (p == std::string::npos) return false;
        p = s.find(':', p);
        if (p == std::string::npos) return false;
        p++;
        while (p < s.size() && (s[p] == ' ' || s[p] == '\t')) p++;

        bool neg = false;
        if (p < s.size() && s[p] == '-') { neg = true; p++; }

        long long val = 0;
        bool any = false;
        while (p < s.size() && s[p] >= '0' && s[p] <= '9') {
            any = true;
            val = val * 10 + (s[p] - '0');
            p++;
        }
        if (!any) return false;
        out = (int)(neg ? -val : val);
        return true;
    }

    bool read_from_json(const std::wstring& path, RECT& outLTRB) {
        std::string s = read_text_file_utf8(path);
        if (s.empty()) return false;

        int left=0, top=0, right=0, bottom=0;
        bool hasLTRB =
            extract_int_key(s, "left", left) &&
            extract_int_key(s, "top", top) &&
            extract_int_key(s, "right", right) &&
            extract_int_key(s, "bottom", bottom);

        if (hasLTRB) {
            outLTRB.left = left; outLTRB.top = top; outLTRB.right = right; outLTRB.bottom = bottom;
            return true;
        }

        int x=0,y=0,w=0,h=0;
        bool hasXYWH =
            extract_int_key(s, "x", x) &&
            extract_int_key(s, "y", y) &&
            extract_int_key(s, "width", w) &&
            extract_int_key(s, "height", h);

        if (hasXYWH) {
            outLTRB.left = x;
            outLTRB.top = y;
            outLTRB.right = x + w;
            outLTRB.bottom = y + h;
            return true;
        }
        return false;
    }

    bool file_mtime(const std::wstring& path, FILETIME& ft) {
        WIN32_FILE_ATTRIBUTE_DATA data{};
        if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &data)) return false;
        ft = data.ftLastWriteTime;
        return true;
    }

    static std::wstring exe_dir() {
        wchar_t buf[MAX_PATH]{0};
        DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
        std::wstring p(buf, buf + n);
        size_t pos = p.find_last_of(L"\\/");
        if (pos == std::wstring::npos) return L".";
        return p.substr(0, pos);
    }

    std::wstring default_region_path() {
        wchar_t envbuf[4096];
        DWORD n = GetEnvironmentVariableW(L"SETJA_REGION_FILE", envbuf, 4096);
        if (n > 0 && n < 4096) return std::wstring(envbuf);

        wchar_t tmp[MAX_PATH]{0};
        DWORD tn = GetTempPathW(MAX_PATH, tmp);
        if (tn > 0 && tn < MAX_PATH) {
            return std::wstring(tmp) + L"setja_region.json";
        }
        return exe_dir() + L"\\region.json";
    }
}