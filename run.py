"""CertHub — inicia o servidor local."""
import os
import sys
import threading
import webbrowser
import uvicorn

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8477))


def open_browser():
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass


if __name__ == "__main__":
    if os.environ.get("OPEN_BROWSER", "0") == "1":
        threading.Timer(1.2, open_browser).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")

