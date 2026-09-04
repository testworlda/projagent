# -*- coding: utf-8 -*-
"""
main.py — Project-Agent 系统入口
启动本地 HTTP 服务（默认端口 8787）：
  - 首次运行自动初始化演示项目（NPU 芯片）
  - 提供 REST API 与静态 Web GUI
用法：python3 -m server.main [--port 8787] [--reset]
"""
import argparse
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DIR = os.path.join(BASE_DIR, "web")


def build_system(reset=False):
    from server.core.system import ProjectSystem
    if reset:
        import shutil
        shutil.rmtree(DATA_DIR, ignore_errors=True)
    system = ProjectSystem(DATA_DIR)
    if not system.project:
        from server.seed.demo_npu import seed
        seed(system)
    return system


class Handler(BaseHTTPRequestHandler):
    system = None

    # -- 静态资源 ----------------------------------------------------------
    def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        # 防目录穿越
        rel = os.path.normpath(path.lstrip("/"))
        if rel.startswith(".."):
            self.send_error(403)
            return
        fp = os.path.join(WEB_DIR, rel)
        if not os.path.isfile(fp):
            self.send_error(404)
            return
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }.get(os.path.splitext(fp)[1], "application/octet-stream")
        with open(fp, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # -- 请求入口 ----------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            from server.api import ApiRouter
            router = ApiRouter(self.system)
            router.handle(self, "GET", path, parsed.query, None)
        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        from server.api import ApiRouter
        router = ApiRouter(self.system)
        router.handle(self, "POST", path, parsed.query, body)

    def log_message(self, fmt, *args):  # noqa
        pass


def main():
    parser = argparse.ArgumentParser(description="Project-Agent 多智能体项目管理系统")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--reset", action="store_true", help="重置并重建演示数据")
    args = parser.parse_args()
    Handler.system = build_system(reset=args.reset)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("=" * 60)
    print("  Project-Agent 多智能体项目管理系统")
    print("  项目: %s" % Handler.system.project.get("name", "-"))
    print("  访问: http://localhost:%d" % args.port)
    print("  API : http://localhost:%d/api/overview" % args.port)
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
