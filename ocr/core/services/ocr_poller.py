import threading
import time

import core.runtime.ocr_config as CFG
import core.runtime.ocr_shm as SHM
import core.runtime.ocr_engine as OCR


_latest_lock = threading.Lock()
LATEST_TEXT = ""
LATEST_JSON = {"ok": False, "error": "no_data_yet"}


def _set_latest(payload):
    global LATEST_TEXT, LATEST_JSON
    with _latest_lock:
        LATEST_JSON = payload
        LATEST_TEXT = (payload.get("text") or "").strip()


def get_latest():
    with _latest_lock:
        return LATEST_JSON


def _poller_loop():
    try:
        OCR.POOL.get(lang=CFG.AUTO_LANG, use_gpu=CFG.AUTO_GPU, use_angle_cls=CFG.AUTO_ANGLE)
    except Exception:
        pass

    last_printed = None
    pending_text = None
    pending_since = 0.0

    while True:
        t0 = time.monotonic()

        img, meta_or_err = SHM.read_frame_bgr()
        if img is None:
            _set_latest({"ok": False, "error": meta_or_err})
        else:
            try:
                ocr = OCR.POOL.get(lang=CFG.AUTO_LANG, use_gpu=CFG.AUTO_GPU, use_angle_cls=CFG.AUTO_ANGLE)
                result = OCR.POOL.run_ocr(ocr, img, cls=CFG.AUTO_CLS)

                text_joined, texts, boxs, scores, avg_conf = OCR.extract_from_paddle_result(result)

                payload = {
                    "ok": True,
                    "text": text_joined,
                    "texts": texts,
                    "boxs": boxs,
                    "scores": scores,
                    "avg_conf": avg_conf,
                    "lang": CFG.AUTO_LANG,
                    "gpu": bool(CFG.AUTO_GPU),
                    "source": "shm_auto",
                    "frame": meta_or_err,
                }
                _set_latest(payload)

                cur_text = text_joined.strip()
                if CFG.STABLE_MS <= 0:
                    if cur_text and cur_text != last_printed:
                        print(cur_text, flush=True)
                        last_printed = cur_text
                else:
                    now = time.monotonic()
                    if pending_text is None or cur_text != pending_text:
                        pending_text = cur_text
                        pending_since = now
                    else:
                        stable_for_ms = (now - pending_since) * 1000.0
                        if cur_text and stable_for_ms >= CFG.STABLE_MS and cur_text != last_printed:
                            print(cur_text, flush=True)
                            last_printed = cur_text

            except Exception as e:
                _set_latest({"ok": False, "error": str(e)})

        elapsed_ms = (time.monotonic() - t0) * 1000.0
        sleep_ms = max(0.0, CFG.POLL_INTERVAL_MS - elapsed_ms)
        time.sleep(sleep_ms / 1000.0)


def start():
    t = threading.Thread(target=_poller_loop, daemon=True)
    t.start()
    return t
