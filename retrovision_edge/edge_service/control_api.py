"""HTTP server ligero para exponer snapshots del edge en vivo."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class EdgeControlApiServer:
    """Servidor HTTP mínimo para snapshots de la cámara procesada por el edge."""

    def __init__(
        self,
        pipeline,
        host: str,
        port: int,
        edge_node_id: str = "",
        edge_api_key: str = "",
    ) -> None:
        self.pipeline = pipeline
        self.host = host
        self.port = port
        self.edge_node_id = edge_node_id
        self.edge_api_key = edge_api_key
        self.logger = logging.getLogger(self.__class__.__name__)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        handler = self._build_handler()
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.logger.info("Control API escuchando en http://%s:%s", self.host, self.port)

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        self._thread = None

    def _build_handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path != "/snapshot":
                    self._send_json(404, {"detail": "Not found"})
                    return

                if not self._is_authorized():
                    self._send_json(403, {"detail": "Forbidden"})
                    return

                query = parse_qs(parsed.query)
                requested_camera_id = (query.get("camera_id") or [""])[0]
                if requested_camera_id and requested_camera_id != outer.pipeline.camera_id:
                    self._send_json(404, {"detail": "Camera not served by this edge instance."})
                    return

                jpeg_bytes = outer.pipeline.get_latest_frame_jpeg()
                if not jpeg_bytes:
                    self._send_json(503, {"detail": "No snapshot available yet."})
                    return

                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(jpeg_bytes)

            def log_message(self, format, *args):
                return

            def _is_authorized(self) -> bool:
                if not outer.edge_node_id or not outer.edge_api_key:
                    return True
                return (
                    self.headers.get("X-Edge-Node-Id", "").strip() == outer.edge_node_id
                    and self.headers.get("X-Edge-Api-Key", "").strip() == outer.edge_api_key
                )

            def _send_json(self, status_code: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler
