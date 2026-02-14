// rs_main.cpp
// Build: cl /EHsc /nologo rs_main.cpp

#define UNICODE
#define _UNICODE
#include <windows.h>

#include <string>
#include <vector>

static std::wstring get_exe_dir() {
    wchar_t buf[MAX_PATH];
    DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    if (n == 0 || n == MAX_PATH) return L"";
    std::wstring path(buf, n);

    // strip filename
    size_t pos = path.find_last_of(L"\\/");
    if (pos == std::wstring::npos) return L"";
    return path.substr(0, pos);
}

static std::wstring parent_dir(const std::wstring& p) {
    if (p.empty()) return L"";
    size_t end = p.find_last_not_of(L"\\/");
    if (end == std::wstring::npos) return L"";
    size_t pos = p.find_last_of(L"\\/", end);
    if (pos == std::wstring::npos) return L"";
    return p.substr(0, pos);
}

static std::wstring resolve_python_exe() {
    wchar_t localApp[MAX_PATH] = L"";
    DWORD n = GetEnvironmentVariableW(L"LOCALAPPDATA", localApp, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return L"python.exe";

    std::wstring venvPython = std::wstring(localApp) + L"\\SETJA\\setja_stable\\Scripts\\python.exe";
    DWORD attrs = GetFileAttributesW(venvPython.c_str());
    if (attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY))
        return venvPython;
    return L"python.exe";
}

// Build environment block: inherit current env + override PYTHONPATH
static std::vector<wchar_t> build_env_with_pythonpath(const std::wstring& pythonpath) {
    LPWCH env = GetEnvironmentStringsW();
    std::vector<wchar_t> out;

    if (env) {
        // Copy all existing variables EXCEPT existing PYTHONPATH (we'll override)
        for (LPWCH cur = env; *cur; ) {
            std::wstring entry(cur);
            cur += entry.size() + 1;

            // skip old PYTHONPATH=
            if (entry.size() >= 11) {
                std::wstring prefix = entry.substr(0, 11);
                for (auto& ch : prefix) ch = towupper(ch);
                if (prefix == L"PYTHONPATH=") continue;
            }

            out.insert(out.end(), entry.begin(), entry.end());
            out.push_back(L'\0');
        }
        FreeEnvironmentStringsW(env);
    }

    std::wstring newVar = L"PYTHONPATH=" + pythonpath;
    out.insert(out.end(), newVar.begin(), newVar.end());
    out.push_back(L'\0');

    // end with extra null
    out.push_back(L'\0');
    return out;
}

int wmain(int argc, wchar_t** argv) {
    // Assume rs_main.exe is inside: <ROOT>\app\rs_main.exe  => ROOT = parent(app)
    std::wstring exeDir = get_exe_dir();
    if (exeDir.empty()) return 2;

    std::wstring root = parent_dir(exeDir); // <ROOT>
    if (root.empty()) return 3;

    std::wstring pythonExe = resolve_python_exe();

    // Python code equivalent to:
    // from core.rs_runtime import run_blocking
    // raise SystemExit(run_blocking())
    std::wstring pyCode =
        L"from core.rs_runtime import run_blocking\n"
        L"raise SystemExit(run_blocking())\n";

    // Build command line: python.exe -c "<code>"
    // Note: Windows CreateProcess needs a mutable buffer.
    std::wstring cmd =
        L"\"" + pythonExe + L"\" -c \"" +
        // escape quotes in code if any (we don't have quotes here)
        pyCode + L"\"";

    STARTUPINFOW si{};
    si.cb = sizeof(si);

    PROCESS_INFORMATION pi{};
    DWORD flags = CREATE_UNICODE_ENVIRONMENT;

    auto envBlock = build_env_with_pythonpath(root);

    // Working directory = ROOT (like your sys.path root logic)
    std::wstring workDir = root;

    std::vector<wchar_t> cmdBuf(cmd.begin(), cmd.end());
    cmdBuf.push_back(L'\0');

    BOOL ok = CreateProcessW(
        nullptr,                 // app name
        cmdBuf.data(),           // command line (mutable)
        nullptr, nullptr,        // security
        FALSE,                   // inherit handles
        flags,                   // creation flags
        envBlock.data(),         // env
        workDir.c_str(),         // current dir
        &si,
        &pi
    );

    if (!ok) {
        DWORD e = GetLastError();
        // Optional: show error
        wchar_t msg[256];
        wsprintfW(msg, L"CreateProcessW failed. GetLastError=%lu", e);
        MessageBoxW(nullptr, msg, L"rs_main", MB_ICONERROR);
        return (int)e;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);

    DWORD exitCode = 0;
    GetExitCodeProcess(pi.hProcess, &exitCode);

    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    return (int)exitCode;
}
