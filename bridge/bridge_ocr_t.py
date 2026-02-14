import time
import requests
import hashlib
import socket
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, Any, Tuple


@dataclass
class BridgeConfig:
    ocr_url: str = "http://127.0.0.1:15188/ocr_shm"
    mt_url: str = "http://127.0.0.1:15199/translate"
    lang: str = "en"
    gpu: int = 1

    poll_interval_ms: int = 80

    ocr_timeout: Tuple[float, float] = (2.0, 5.0)
    mt_timeout: Tuple[float, float] = (2.0, 10.0)

    skip_empty: bool = True

    unique_stream_per_text: bool = True
    stream_id: str = "bridge_ocr"

    # منطق الظهور: 1 ترجم، 2 تخطى، 3 ترجم، 4+ لمدة ثانية تخطى، نص جديد يعيد الدورة
    similarity_threshold: float = 0.8  # نسبة التشابه لتحديد "نفس النص"
    cooldown_sec: float = 1.0  # ثانية تخطي بعد الظهور الثالث


def _text_similarity(a: str, b: str) -> float:
    """نسبة التشابه بين نصين 0.0 .. 1.0"""
    a = (a or "").strip()
    b = (b or "").strip()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _appearance_gate(
    cur_text: str,
    state: dict,
    similarity_threshold: float,
    cooldown_sec: float,
) -> bool:
    """
    منطق الظهور:
    - ظهور 1: ترجم
    - ظهور 2 (مشابه 80%): تخطى
    - ظهور 3 (مشابه 80%): ترجم
    - ظهور 4+ لمدة ثانية: تخطى
    - نص جديد (<80% مشابه): ترجم وأعد الدورة
    """
    cur_text = (cur_text or "").strip()
    now = time.monotonic()

    prev = state.get("prev_ocr_text")
    count = state.get("appearance_count", 0)
    cooldown_until = state.get("cooldown_until", 0.0)

    # نص جديد (مختلف أو أول مرة)
    if prev is None or prev == "" or _text_similarity(cur_text, prev) < similarity_threshold:
        state["prev_ocr_text"] = cur_text
        state["appearance_count"] = 1
        state["last_sent_text"] = cur_text
        return True  # ظهور 1: ترجم

    # نفس النص (مشابه ≥ threshold)
    count += 1
    state["prev_ocr_text"] = cur_text
    state["appearance_count"] = count

    if count == 1:
        # لا يصل هنا عادة (دخلنا من الفرع الأول)
        return True
    if count == 2:
        return False  # ظهور 2: تخطى
    if count == 3:
        state["cooldown_until"] = now + cooldown_sec
        state["last_sent_text"] = cur_text
        return True  # ظهور 3: ترجم
    # ظهور 4+
    if now < cooldown_until:
        return False  # لمدة ثانية: تخطى
    return False  # بعد الثانية: نفس النص، تخطى


def _fetch_ocr_text(session: requests.Session, cfg: BridgeConfig) -> Dict[str, Any]:
    params = {"lang": cfg.lang, "gpu": str(cfg.gpu)}
    r = session.post(cfg.ocr_url, params=params, data=b"", timeout=cfg.ocr_timeout)
    return r.json()


def _send_to_translator(session: requests.Session, cfg: BridgeConfig, text: str) -> Dict[str, Any]:
    if cfg.unique_stream_per_text:
        sid = "bridge_" + hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
    else:
        sid = cfg.stream_id

    payload = {"text": text, "stream_id": sid}
    r = session.post(cfg.mt_url, json=payload, timeout=cfg.mt_timeout)
    return r.json()

def _can_connect(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_ports(
    targets, 
    *,
    label: str = "[WAIT]",
    check_interval: float = 0.4,
):
    last_missing = None

    while True:
        missing = []
        for name, host, port in targets:
            if not _can_connect(host, port):
                missing.append(name)

        if not missing:
            return

        missing_str = ", ".join(missing)
        if missing_str != last_missing:
            last_missing = missing_str
            print(f"{label} waiting for: {missing_str}")

        time.sleep(check_interval)

def run_bridge(
    cfg: BridgeConfig,
    on_result,
    on_error=None,
    stop_pred=None,
) -> None:
    s = requests.Session()

    state = {
        "prev_ocr_text": None,
        "appearance_count": 0,
        "cooldown_until": 0.0,
        "last_sent_text": None,
    }
    
    http_fail_count = 0
    last_http_print = 0.0

    def emit_err(kind: str, info: str):
        if on_error:
            on_error(kind, info)

    while True:
        if stop_pred and stop_pred():
            break

        t0 = time.monotonic()
        try:
            ocr_j = _fetch_ocr_text(s, cfg)
            http_fail_count = 0

            if not ocr_j.get("ok", False):
                emit_err("OCR", str(ocr_j.get("error", "unknown_error")))
            else:
                cur_text = (ocr_j.get("text") or "").strip()

                if cfg.skip_empty and not cur_text:
                    pass
                else:
                    if _appearance_gate(
                        cur_text,
                        state,
                        cfg.similarity_threshold,
                        cfg.cooldown_sec,
                    ):
                        mt_j = _send_to_translator(s, cfg, cur_text)

                        if not mt_j.get("ok", False) and not (mt_j.get("text") or mt_j.get("lines")):
                            emit_err("MT", str(mt_j.get("error", "unknown_error")))
                        else:
                            on_result(cur_text, mt_j)

        except requests.RequestException as e:
            http_fail_count += 1

            # backoff خفيف: يزيد لحد 2 ثواني
            backoff = min(2.0, 0.2 * (2 ** min(4, http_fail_count)))
            time.sleep(backoff)

            # بدل spam: نبلّغ كل 2 ثانية فقط
            now = time.monotonic()
            if on_error and (now - last_http_print >= 2.0):
                last_http_print = now
                on_error("HTTP", str(e))

        except ValueError as e:
            emit_err("JSON", str(e))
        except KeyboardInterrupt:
            break

        elapsed_ms = (time.monotonic() - t0) * 1000.0
        sleep_ms = max(0.0, cfg.poll_interval_ms - elapsed_ms)
        time.sleep(sleep_ms / 1000.0)
