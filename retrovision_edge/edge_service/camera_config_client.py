"""Cliente HTTP ligero para perfiles de cámara almacenados en el backend."""

from __future__ import annotations

import json
from typing import Any, Optional
from urllib import error, request


class CameraConfigClient:
    """Gestiona lectura y escritura de perfiles de cámara vía API REST."""

    def __init__(
        self,
        base_url: str,
        token: str = "",
        username: str = "",
        password: str = "",
        edge_node_id: str = "",
        edge_api_key: str = "",
        timeout_seconds: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.username = username.strip()
        self.password = password
        self.edge_node_id = edge_node_id.strip()
        self.edge_api_key = edge_api_key.strip()
        self.timeout_seconds = timeout_seconds

    def get_camera_profile(self, camera_id: str) -> Optional[dict[str, Any]]:
        """Obtiene el perfil de una cámara por su camera_id."""
        try:
            return self._request_json(
                method="GET",
                path=f"/api/cameras/{camera_id}/",
            )
        except error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def upsert_camera_profile(
        self,
        camera_id: str,
        roi_polygon: list[list[int]],
        queue_wait_threshold: float,
        video_source: Optional[str] = None,
    ) -> dict[str, Any]:
        """Crea o actualiza el perfil de cámara asociado al ROI dibujado."""
        existing_profile = self.get_camera_profile(camera_id)
        payload = {
            "camera_id": camera_id,
            "roi_polygon": roi_polygon,
            "queue_wait_threshold": queue_wait_threshold,
        }
        if video_source:
            payload["video_source"] = video_source

        if existing_profile is None:
            return self._request_json(
                method="POST",
                path="/api/cameras/",
                payload=payload,
            )

        return self._request_json(
            method="PATCH",
            path=f"/api/cameras/{camera_id}/",
            payload=payload,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[dict[str, Any]] = None,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        """Ejecuta una petición JSON y retorna la respuesta parseada."""
        headers = {"Content-Type": "application/json"}
        if authenticated:
            if self.edge_node_id and self.edge_api_key:
                headers["X-Edge-Node-Id"] = self.edge_node_id
                headers["X-Edge-Api-Key"] = self.edge_api_key
            else:
                token = self._get_access_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"

        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            raw_content = response.read()
            if not raw_content:
                return {}
            return json.loads(raw_content.decode("utf-8"))

    def _get_access_token(self) -> str:
        """Retorna un token utilizable, autenticando contra JWT si hace falta."""
        if self.token:
            return self.token

        if not self.username or not self.password:
            return ""

        response = self._request_json(
            method="POST",
            path="/api/token/",
            payload={
                "username": self.username,
                "password": self.password,
            },
            authenticated=False,
        )
        self.token = str(response.get("access", "")).strip()
        return self.token
