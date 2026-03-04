"""
VibeVtuber Text Driver Service — NLP Only

Analyzes text emotion using Qwen API and returns structured results.

HTTP server (default port 7778):
  POST /speak   { "text": "..." }  → { ok, emotion, intensity, blendshapes }
  GET  /status  → { "ok": true }
"""

import json
import os
import traceback
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingTCPServer

from text_analyzer import TextAnalyzer


def load_config() -> dict:
    path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_analyzer: TextAnalyzer = None


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            if self.path == "/speak":
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                text = body.get("text", "").strip()
                if not text:
                    self._json(400, {"ok": False, "error": "text 不能为空"})
                    return
                print(f"[TextDriver] 分析: {text[:40]}{'...' if len(text) > 40 else ''}")
                result = _analyzer.analyze(text)
                print(f"[TextDriver] 情感={result['emotion']}  强度={result['intensity']:.2f}")
                self._json(200, {"ok": True, **result})
            else:
                self._json(404, {"error": "not found"})
        except Exception:
            traceback.print_exc()
            try:
                self._json(500, {"ok": False, "error": "服务内部错误，请查看日志"})
            except Exception:
                pass

    def do_GET(self):
        try:
            if self.path == "/status":
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "not found"})
        except Exception:
            pass

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress default HTTP logs


class _ThreadingHTTPServer(ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    global _analyzer
    config = load_config()
    qwen = config.get("qwen", {})

    if not qwen.get("api_key"):
        print("[TextDriver] 警告: Qwen API Key 未配置，请在 config.json 中填入 api_key")

    _analyzer = TextAnalyzer(
        api_key=qwen.get("api_key", ""),
        model=qwen.get("model", "qwen-turbo"),
        base_url=qwen.get("base_url",
                           "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )

    srv = config.get("server", {})
    host = srv.get("host", "127.0.0.1")
    port = srv.get("port", 7778)

    print(f"[TextDriver] 服务已启动: http://{host}:{port}")
    print(f"[TextDriver] 模型: {qwen.get('model', 'qwen-turbo')}")
    print(f"[TextDriver] 等待指令...")

    server = _ThreadingHTTPServer((host, port), _Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
