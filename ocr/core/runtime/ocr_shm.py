import ctypes
from ctypes import wintypes
import numpy as np
import cv2

_SHM_NAME  = "Local\\SETJA_OCR_FRAME_V1"
_SHM_MAGIC = 0x4D464A53
_SHM_FMT_BGRA8 = 1

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

OpenFileMappingW = kernel32.OpenFileMappingW
OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
OpenFileMappingW.restype = wintypes.HANDLE

MapViewOfFile = kernel32.MapViewOfFile
MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
MapViewOfFile.restype = wintypes.LPVOID

UnmapViewOfFile = kernel32.UnmapViewOfFile
UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
UnmapViewOfFile.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

FILE_MAP_READ = 0x0004


class _ShmHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("seq", ctypes.c_long),  # LONG
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
        ("stride", ctypes.c_int32),
        ("format", ctypes.c_int32),
        ("region_left", ctypes.c_int32),
        ("region_top", ctypes.c_int32),
        ("data_bytes", ctypes.c_uint32),
    ]


_shm_handle = None
_shm_view = None
_shm_view_size = 0


def shm_close():
    global _shm_handle, _shm_view, _shm_view_size
    if _shm_view:
        UnmapViewOfFile(_shm_view)
    if _shm_handle:
        CloseHandle(_shm_handle)
    _shm_view = None
    _shm_handle = None
    _shm_view_size = 0


def _shm_open_min():
    global _shm_handle, _shm_view, _shm_view_size
    if _shm_handle and _shm_view and _shm_view_size >= ctypes.sizeof(_ShmHeader):
        return True

    shm_close()

    h = OpenFileMappingW(FILE_MAP_READ, False, _SHM_NAME)
    if not h:
        return False

    view = MapViewOfFile(h, FILE_MAP_READ, 0, 0, ctypes.sizeof(_ShmHeader))
    if not view:
        CloseHandle(h)
        return False

    _shm_handle = h
    _shm_view = view
    _shm_view_size = ctypes.sizeof(_ShmHeader)
    return True


def _shm_remap_full(total_size: int):
    global _shm_view, _shm_view_size

    if _shm_view and _shm_view_size == total_size:
        return True

    if _shm_view:
        UnmapViewOfFile(_shm_view)
        _shm_view = None
        _shm_view_size = 0

    view = MapViewOfFile(_shm_handle, FILE_MAP_READ, 0, 0, total_size)
    if not view:
        shm_close()
        return False

    _shm_view = view
    _shm_view_size = total_size
    return True


def read_frame_bgr(max_spin: int = 200):
    if not _shm_open_min():
        return None, "Waiting for screen capture…"

    hdr0 = _ShmHeader.from_address(_shm_view)

    if hdr0.magic != _SHM_MAGIC or hdr0.version != 1:
        return None, "Capture stream is not ready yet."
    if hdr0.format != _SHM_FMT_BGRA8:
        return None, "Capture format not supported."
    if hdr0.width <= 0 or hdr0.height <= 0 or hdr0.stride <= 0 or hdr0.data_bytes <= 0:
        return None, "Capture region is invalid."

    total_size = ctypes.sizeof(_ShmHeader) + int(hdr0.data_bytes)
    if not _shm_remap_full(total_size):
        return None, "Cannot read the capture stream."

    hdr = _ShmHeader.from_address(_shm_view)
    base = (ctypes.c_ubyte * total_size).from_address(_shm_view)
    offset = ctypes.sizeof(_ShmHeader)

    for _ in range(max_spin):
        s1 = hdr.seq
        if s1 & 1:
            continue

        raw = np.frombuffer(base, dtype=np.uint8, count=int(hdr.data_bytes), offset=offset).copy()

        s2 = hdr.seq
        if s1 == s2 and not (s2 & 1):
            h = int(hdr.height)
            w = int(hdr.width)
            stride = int(hdr.stride)

            rows = raw.reshape((h, stride))
            bgra = rows[:, : w * 4].reshape((h, w, 4))
            bgr = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)

            meta = {
                "w": w,
                "h": h,
                "left": int(hdr.region_left),
                "top": int(hdr.region_top),
            }
            return bgr, meta

    return None, "Waiting for a stable frame…"
