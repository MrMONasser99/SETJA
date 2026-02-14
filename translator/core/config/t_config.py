import os

os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

MODEL_DIR = os.path.join(APP_ROOT, "translator_model")
TOKENIZER_DIR = os.path.join(APP_ROOT, "hf_tokenizer")

print(f"DEBUG: Model should be at: {MODEL_DIR}")

DEVICE = "cuda"
DEVICE_INDEX = 0
COMPUTE_TYPE = "int8"

BEAM_SIZE = 1
MAX_DECODING_LENGTH = 128
BATCH_SIZE = 16

CACHE_MAX = 4000
SPEAKER_CACHE_MAX = 2000

STABLE_MS = 120

HOST = "127.0.0.1"
PORT = 15199
