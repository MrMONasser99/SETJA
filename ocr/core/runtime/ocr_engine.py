import threading
from paddleocr import PaddleOCR

_LANG_ALIASES = {
    "ar": "arabic",
    "ja": "japan",
    "jp": "japan",
    "ko": "korean",
    "kr": "korean",
    "zh": "ch",
    "chs": "ch",
    "zh-cn": "ch",
    "zh-hans": "ch",
    "cht": "chinese_cht",
    "zh-tw": "chinese_cht",
    "zh-hant": "chinese_cht",
    "de": "german",
    "fr": "french",
    "en": "en",
    "ch": "ch",
    "japan": "japan",
    "korean": "korean",
    "german": "german",
    "french": "french",
    "chinese_cht": "chinese_cht",
}

class PaddleOcrPool:
    def __init__(self, show_log: bool = False):
        self._cache = {}
        self._lock = threading.Lock()
        self._show_log = show_log
        self._run_lock = threading.Lock()

    def get(self, lang: str, use_gpu: bool, use_angle_cls: bool):
        # توحيد اسم اللغة بناءً على القاموس أعلاه
        lang = (lang or "en").strip().lower()
        lang = _LANG_ALIASES.get(lang, lang)
        key = (lang, bool(use_gpu), bool(use_angle_cls))

        with self._lock:
            # التأكد من وجود الكائن في الكاش
            ocr_instance = self._cache.get(key)
            if ocr_instance is not None:
                return ocr_instance

            # التعديل الأساسي: إنشاء الكائن في متغير محلي أولاً ثم تخزينه
            # قمنا بتثبيت lang="en" لضمان الحصول على النسخة الإنجليزية فقط كما طلبت
            ocr_instance = PaddleOCR(
                use_angle_cls=use_angle_cls, 
                lang="en", 
                use_gpu=use_gpu, 
                show_log=self._show_log,
                rec_model_dir=None,
                det_model_dir=None
            )
            
            self._cache[key] = ocr_instance
            return ocr_instance

    def run_ocr(self, ocr: PaddleOCR, img_bgr, cls: bool):
        with self._run_lock:
            # تأكد أن ocr ليس None قبل التشغيل
            if ocr is None:
                raise ValueError("OCR engine is not initialized. Check your configurations.")
            return ocr.ocr(img_bgr, cls=bool(cls))


def extract_from_paddle_result(result):
    texts = []
    boxs = []
    scores = []
    
    # PaddleOCR يرجع قائمة تحتوي على نتائج كل صفحة (نحن نتعامل مع صورة واحدة لذا نأخذ result[0])
    if result and len(result) > 0 and result[0]:
        for line in result[0]:
            box = line[0]
            text = line[1][0]
            score = float(line[1][1])
            boxs.append([[int(p[0]), int(p[1])] for p in box])
            texts.append(text)
            scores.append(score)

    text_joined = "\n".join(texts).strip()
    avg_conf = (sum(scores) / len(scores)) if scores else 0.0
    return text_joined, texts, boxs, scores, avg_conf


POOL = PaddleOcrPool(show_log=False)