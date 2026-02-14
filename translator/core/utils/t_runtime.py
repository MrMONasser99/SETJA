import time
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self._d = OrderedDict()

    def get(self, k):
        if k in self._d:
            self._d.move_to_end(k)
            return self._d[k]
        return None

    def set(self, k, v):
        self._d[k] = v
        self._d.move_to_end(k)
        if len(self._d) > self.max_size:
            self._d.popitem(last=False)

class StabilityGate:
    def __init__(self, stable_ms: int):
        self.stable_ms = max(0, int(stable_ms))
        self._state = {}

    def allow(self, stream_id: str, key: str) -> bool:
        if self.stable_ms == 0:
            return True
        now = time.perf_counter()
        st = self._state.get(stream_id)
        if st is None:
            self._state[stream_id] = (key, now)
            return True
        last_key, change_t = st
        if key != last_key:
            self._state[stream_id] = (key, now)
            return False
        return (now - change_t) * 1000.0 >= self.stable_ms
