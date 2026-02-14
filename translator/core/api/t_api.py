from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from core.config.t_config import APP_ROOT, MODEL_DIR, TOKENIZER_DIR, DEVICE, COMPUTE_TYPE
from core.utils.t_engine import RealTimeMT

app = FastAPI(title="SETJA Translator", version="1.0")

_mt: Optional[RealTimeMT] = None


class TranslateReq(BaseModel):
    text: Optional[str] = None
    lines: Optional[List[str]] = None
    stream_id: Optional[str] = "subtitle"


class TranslateResp(BaseModel):
    ok: bool
    lines: Optional[List[str]] = None
    ms: float
    waiting_for_stability: bool = False
    error: Optional[str] = None


@app.on_event("startup")
def startup():
    global _mt
    _mt = RealTimeMT()

    print(f"Translator API Running")


@app.get("/health")
def health():
    return {
        "ok": True,
        "app_root": APP_ROOT,
        "model_dir": MODEL_DIR,
        "tokenizer_dir": TOKENIZER_DIR,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
    }


@app.post("/translate", response_model=TranslateResp)
def translate(req: TranslateReq):
    global _mt
    try:
        if _mt is None:
            _mt = RealTimeMT()

        payload = req.lines
        if payload is None and isinstance(req.text, str):
            payload = req.text.splitlines()

        out, ms = _mt.translate_lines(payload, stream_id=req.stream_id or "subtitle")
        if out is None:
            return TranslateResp(ok=True, lines=None, ms=ms, waiting_for_stability=True)

        return TranslateResp(ok=True, lines=out, ms=ms)

    except Exception as e:
        return TranslateResp(ok=False, ms=0.0, error=str(e))
