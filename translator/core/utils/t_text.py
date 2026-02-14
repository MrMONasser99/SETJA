import re

def squash_spaces(s: str) -> str:
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()

def normalize_punct(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("\u2014", "-").replace("\u2013", "-")
    s = s.replace("…", "...")
    s = re.sub(r"\s+([,.!?;:])", r"\1", s)
    return squash_spaces(s)

def cache_key(s: str) -> str:
    return normalize_punct(s).lower()

def try_split_speaker(line: str):
    m = re.match(r"^\s*([^:]{1,60})\s*:\s*(.+?)\s*$", line)
    if not m:
        return None, line
    return m.group(1).strip(), m.group(2).strip()

def contains_latin(s: str) -> bool:
    return bool(re.search(r"[A-Za-z]", s or ""))

def looks_bad_speaker(ar: str) -> bool:
    if not ar:
        return True
    if contains_latin(ar):
        return True
    if ":" in ar:
        return True
    if len(ar) > 40:
        return True
    return False

_DIGRAPHS = [
    ("sh", "ش"), ("ch", "تش"), ("th", "ث"), ("kh", "خ"),
    ("gh", "غ"), ("ph", "ف"), ("ck", "ك"), ("qu", "كو"),
]
_SINGLE = {
    "a": "ا", "b": "ب", "c": "ك", "d": "د", "e": "ي", "f": "ف", "g": "ج",
    "h": "ه", "i": "ي", "j": "ج", "k": "ك", "l": "ل", "m": "م", "n": "ن",
    "o": "و", "p": "ب", "q": "ق", "r": "ر", "s": "س", "t": "ت", "u": "و",
    "v": "ف", "w": "و", "x": "كس", "y": "ي", "z": "ز",
}

def transliterate_to_ar(s: str) -> str:
    s0 = re.sub(r"[^A-Za-z0-9 #_-]", "", s or "").strip()
    if not s0:
        return "المتحدث"
    low = s0.lower()

    out = []
    i = 0
    while i < len(low):
        if low[i].isdigit():
            out.append(low[i])
            i += 1
            continue

        if low[i] in [" ", "#", "_", "-"]:
            out.append(" " if low[i] == " " else low[i])
            i += 1
            continue

        matched = False
        for dg, ar in _DIGRAPHS:
            if low.startswith(dg, i):
                out.append(ar)
                i += len(dg)
                matched = True
                break
        if matched:
            continue

        ch = low[i]
        out.append(_SINGLE.get(ch, ""))
        i += 1

    return squash_spaces("".join(out)) or "المتحدث"
