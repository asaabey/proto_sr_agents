import logging
import threading
import queue
from typing import Callable, Set, Tuple

_listeners: Set[Callable[[str], None]] = set()
_lock = threading.Lock()


class BroadcastHandler(logging.Handler):
    """Logging handler that broadcasts formatted log lines to registered callbacks."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            return
        with _lock:
            listeners = list(_listeners)
        for cb in listeners:
            try:
                cb(msg)
            except Exception:
                # Never let a bad callback break logging
                pass


_broadcast_handler = BroadcastHandler()
_broadcast_handler.setLevel(logging.INFO)
_broadcast_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
)


def ensure_handler_installed() -> None:
    root = logging.getLogger()
    if not any(isinstance(h, BroadcastHandler) for h in root.handlers):
        root.addHandler(_broadcast_handler)


def register_listener():
    """Register a new listener; returns (queue, callback) so caller can drain queue and later unregister."""
    q: "queue.Queue[str]" = queue.Queue()

    def _cb(line: str):
        q.put(line)

    with _lock:
        _listeners.add(_cb)
    return q, _cb


def unregister_listener(cb: Callable[[str], None]):
    with _lock:
        _listeners.discard(cb)
