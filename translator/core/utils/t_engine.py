import time

import ctranslate2
import transformers

from core.config.t_config import (
    MODEL_DIR,
    TOKENIZER_DIR,
    DEVICE,
    DEVICE_INDEX,
    COMPUTE_TYPE,
    BEAM_SIZE,
    MAX_DECODING_LENGTH,
    BATCH_SIZE,
    CACHE_MAX,
    SPEAKER_CACHE_MAX,
    STABLE_MS,
)

from core.utils.t_text import (
    normalize_punct,
    cache_key,
    try_split_speaker,
    looks_bad_speaker,
    transliterate_to_ar,
)

from core.utils.t_runtime import LRUCache, StabilityGate


class RealTimeMT:
    def __init__(self):
        self.translator = ctranslate2.Translator(
            MODEL_DIR,
            device=DEVICE,
            device_index=DEVICE_INDEX,
            compute_type=COMPUTE_TYPE,
        )

        self.tokenizer = transformers.MarianTokenizer.from_pretrained(
            TOKENIZER_DIR,
            local_files_only=True,
        )

        self.cache = LRUCache(CACHE_MAX)
        self.speaker_cache = LRUCache(SPEAKER_CACHE_MAX)
        self.gate = StabilityGate(STABLE_MS)

        self._warmup()

    def _encode_to_tokens(self, text: str):
        enc = self.tokenizer(
            text,
            add_special_tokens=True,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        ids = enc["input_ids"]
        return self.tokenizer.convert_ids_to_tokens(ids)

    def _decode_from_tokens(self, tokens):
        ids = self.tokenizer.convert_tokens_to_ids(tokens)
        return self.tokenizer.decode(ids, skip_special_tokens=True)

    def _warmup(self):
        toks = self._encode_to_tokens("Hello!")
        _ = self.translator.translate_batch([toks], beam_size=1, max_decoding_length=32)

    def _translate_batch_strings(self, strings, max_len=MAX_DECODING_LENGTH):
        if not strings:
            return [], 0.0

        batch_tokens = [self._encode_to_tokens(s) for s in strings]

        t0 = time.perf_counter()
        results = []

        for i in range(0, len(batch_tokens), BATCH_SIZE):
            chunk = batch_tokens[i:i + BATCH_SIZE]
            out = self.translator.translate_batch(
                chunk,
                beam_size=BEAM_SIZE,
                max_decoding_length=max_len,
            )
            results.extend(out)

        t1 = time.perf_counter()

        translations = []
        for r in results:
            out_tokens = r.hypotheses[0]
            translations.append(self._decode_from_tokens(out_tokens))

        return translations, (t1 - t0) * 1000.0

    def _translate_speaker_runtime(self, speaker: str) -> str:
        spk_norm = normalize_punct(speaker)
        key = cache_key(spk_norm)

        cached = self.speaker_cache.get(key)
        if cached is not None:
            return cached

        ar_list, _ = self._translate_batch_strings([spk_norm], max_len=32)
        ar = (ar_list[0] if ar_list else "").strip()

        if looks_bad_speaker(ar):
            ar = transliterate_to_ar(speaker)

        self.speaker_cache.set(key, ar)
        return ar

    def translate_lines(self, lines, stream_id="subtitle"):
        if isinstance(lines, str):
            lines = [lines]

        norm_lines = [normalize_punct(s) for s in lines if s is not None]
        group_key = cache_key("\n".join(norm_lines))

        if not self.gate.allow(stream_id, group_key):
            last = self.cache.get(f"STREAM::{stream_id}")
            return (last, 0.0) if last is not None else (None, 0.0)

        cached = self.cache.get(group_key)
        if cached is not None:
            self.cache.set(f"STREAM::{stream_id}", cached)
            return cached, 0.0

        speakers = []
        messages = []
        for s in norm_lines:
            spk, msg = try_split_speaker(s)
            speakers.append(spk)
            messages.append(msg)

        msg_trans, t_ms = self._translate_batch_strings(messages, max_len=MAX_DECODING_LENGTH)

        out_lines = []
        for spk, msg_ar in zip(speakers, msg_trans):
            if spk is None:
                out_lines.append(msg_ar)
            else:
                spk_ar = self._translate_speaker_runtime(spk)
                out_lines.append(f"{spk_ar}: {msg_ar}")

        self.cache.set(group_key, out_lines)
        self.cache.set(f"STREAM::{stream_id}", out_lines)

        return out_lines, t_ms