"""Start the same local API in Android/iOS app storage, without a PC or web host."""
import os
from pathlib import Path
import threading

_server = None
_lock = threading.Lock()


def start(data_directory):
    global _server
    with _lock:
        if _server is None:
            data = Path(data_directory)
            data.mkdir(parents=True, exist_ok=True)
            # Desktop server-loaded configuration must never point inside an immutable bundle.
            os.environ['PAPER_AI_DATA_DIR'] = str(data)
            from server import make_server
            _server = make_server(8765, data/'paperai.sqlite3')
            threading.Thread(target=_server.serve_forever, daemon=True, name='paper-ai-local').start()
    return f'http://127.0.0.1:{_server.server_port}'
