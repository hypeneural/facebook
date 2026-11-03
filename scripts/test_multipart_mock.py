"""Teste unitário do executor multipart streaming contra um mock HTTP local."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import http.server
import json
import socketserver
import tempfile
import threading
import urllib.parse
from scripts.daily_tick import send_multipart

class MockHandler(http.server.BaseHTTPRequestHandler):
    received_bytes = 0
    received_headers = {}

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        MockHandler.received_headers = dict(self.headers)
        # Lê em chunks de 64 KB para simular streaming
        read_total = 0
        while read_total < content_length:
            chunk = self.rfile.read(min(65536, content_length - read_total))
            if not chunk:
                break
            read_total += len(chunk)
        MockHandler.received_bytes = read_total

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = {
            "status": "SUBMITTED_UNVERIFIED",
            "operation_id": "mock-op-uuid-12345",
            "message": "Mock upload recebido com sucesso"
        }
        self.wfile.write(json.dumps(resp).encode("utf-8"))

    def log_message(self, format, *args):
        pass

def test_streaming():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        file1 = tdp / "sample.bin"
        # Cria arquivo de 5 MB
        file1.write_bytes(b"A" * (5 * 1024 * 1024))

        # Inicia mock server em porta efêmera
        # Como send_multipart tem host fixo 8108 no código, testamos a lógica de segmentos e conexão
        # adaptando para testar a função send_multipart modificando temporariamente a porta.
        with socketserver.TCPServer(("127.0.0.1", 0), MockHandler) as httpd:
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.handle_request)
            t.start()

            # Executa com monkeypatch da porta na conexão
            import http.client
            orig_conn = http.client.HTTPConnection
            def patched_conn(host, p, timeout=900):
                return orig_conn("127.0.0.1", port, timeout=timeout)
            http.client.HTTPConnection = patched_conn

            try:
                resp = send_multipart(
                    url="https://www.facebook.com/groups/389335997243726/",
                    caption="Legenda de teste streaming",
                    files=[file1]
                )
            finally:
                http.client.HTTPConnection = orig_conn
                t.join()

        result = {
            "api_response": resp,
            "bytes_streamed": MockHandler.received_bytes,
            "content_type_header": MockHandler.received_headers.get("Content-Type", ""),
            "success": bool(resp.get("status") == "SUBMITTED_UNVERIFIED" and MockHandler.received_bytes > 5 * 1024 * 1024)
        }
        assert result["success"]
        # Pytest functions must return None; __main__ still exits successfully.

if __name__ == "__main__":
    raise SystemExit(test_streaming())
