"""Servidor local do histórico.

A mesma página que vai para o site estático, servida de localhost com os
dados em claro — quem está na própria máquina já tem acesso ao histórico,
então aqui não faz sentido pedir senha.
"""

import http.server
import json
import socketserver
import threading
import webbrowser
from pathlib import Path

from . import config, history

WEB_DIR = Path(__file__).resolve().parent.parent / "docs"


def _payload(account):
    entries = history.read_all(account=account)
    return {
        "generated": history._now_iso(),
        "count": len(entries),
        "entries": entries,
        "local": True,
    }


def make_handler(account):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WEB_DIR), **kwargs)

        def _json(self, payload):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            rota = self.path.rstrip("/").split("?", 1)[0]
            if rota == "/data/history.json":
                self._json(_payload(account))
                return
            # sobrepõe o manifesto versionado, que diz "não tem nada aqui": daqui
            # sai histórico em claro, e a página precisa saber disso para buscá-lo
            if rota == "/data/manifest.json":
                self._json({"local": True, "published": False})
                return
            super().do_GET()

        def log_message(self, *args):
            pass  # o terminal é do usuário, não do servidor

    return Handler


def serve(port: int = 8765, account=None, open_browser: bool = True) -> None:
    account = account or config.load().get("default_account")
    socketserver.TCPServer.allow_reuse_address = True
    # 127.0.0.1, não 0.0.0.0: o histórico não vaza para a rede local
    with socketserver.TCPServer(("127.0.0.1", port), make_handler(account)) as httpd:
        url = f"http://127.0.0.1:{port}/"
        print(f"histórico de '{account}' em {url}  (ctrl-c para parar)")
        if open_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nparado")
