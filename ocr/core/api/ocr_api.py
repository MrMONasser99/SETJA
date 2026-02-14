import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import cv2
import numpy as np

import core.runtime.ocr_engine as PaddleOcrPool
import core.runtime.ocr_shm as SHM
import core.services.ocr_poller as ocr_poller


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, code: int, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError):
            return

    def do_GET(self):
        if self.path.startswith("/health"):
            return self._send_json(200, {"ok": True})

        if self.path.startswith("/latest"):
            latest = ocr_poller.get_latest()
            code = 200 if latest.get("ok") else 503
            return self._send_json(code, latest)

        return self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path not in ("/ocr", "/ocr_shm"):
            return self._send_json(404, {"ok": False, "error": "not_found"})

        qs = parse_qs(u.query)
        lang = (qs.get("lang", ["en"])[0] or "en")
        use_gpu = qs.get("gpu", ["1"])[0] not in ("0", "false", "False")
        use_angle_cls = qs.get("angle", ["0"])[0] in ("1", "true", "True")
        cls_flag = qs.get("cls", ["0"])[0] in ("1", "true", "True")

        if u.path == "/ocr_shm":
            img, meta_or_err = SHM.read_frame_bgr()
            if img is None:
                return self._send_json(503, {"ok": False, "error": meta_or_err})

            try:
                ocr = PaddleOcrPool.POOL.get(lang=lang, use_gpu=use_gpu, use_angle_cls=use_angle_cls)
                result = PaddleOcrPool.POOL.run_ocr(ocr, img, cls=cls_flag)
                text_joined, texts, boxs, scores, avg_conf = PaddleOcrPool.extract_from_paddle_result(result)

                return self._send_json(200, {
                    "ok": True,
                    "text": text_joined,
                    "texts": texts,
                    "boxs": boxs,
                    "scores": scores,
                    "avg_conf": avg_conf,
                    "lang": lang,
                    "gpu": use_gpu,
                    "source": "shm",
                    "frame": meta_or_err,
                })
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": str(e)})

        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return self._send_json(400, {"ok": False, "error": "empty_body"})

        body = self.rfile.read(length)
        arr = np.frombuffer(body, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return self._send_json(400, {"ok": False, "error": "bad_image"})

        try:
            ocr = PaddleOcrPool.POOL.get(lang=lang, use_gpu=use_gpu, use_angle_cls=use_angle_cls)
            result = PaddleOcrPool.POOL.run_ocr(ocr, img, cls=cls_flag)
            text_joined, texts, boxs, scores, avg_conf = PaddleOcrPool.extract_from_paddle_result(result)

            return self._send_json(200, {
                "ok": True,
                "text": text_joined,
                "texts": texts,
                "boxs": boxs,
                "scores": scores,
                "avg_conf": avg_conf,
                "lang": lang,
                "gpu": use_gpu,
                "source": "body",
            })
        except Exception as e:
            return self._send_json(500, {"ok": False, "error": str(e)})


def create_server(host: str, port: int):
    return ThreadingHTTPServer((host, port), Handler)
