"""Herramienta interactiva para dibujar y persistir el ROI de cola por cámara."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv, set_key

from edge_service import EdgeServiceConfig, VideoStreamProcessor
from edge_service.camera_config_client import CameraConfigClient


EDGE_ROOT = Path(__file__).resolve().parent


class RoiSelectionState:
    """Estado mutable del selector interactivo."""

    def __init__(self, initial_points: list[list[int]] | None = None) -> None:
        self.points = [list(point) for point in (initial_points or [])]

    def add_point(self, x: int, y: int) -> None:
        self.points.append([int(x), int(y)])

    def remove_last_point(self) -> None:
        if self.points:
            self.points.pop()

    def clear(self) -> None:
        self.points.clear()


def parse_args() -> argparse.Namespace:
    """Parsea argumentos CLI."""
    parser = argparse.ArgumentParser(description="Selector de ROI para RetroVision Edge")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Archivo .env de la instancia edge a configurar.",
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=5,
        help="Cantidad de frames a avanzar antes de congelar la imagen base.",
    )
    parser.add_argument(
        "--no-backend-sync",
        action="store_true",
        help="Guarda solo en el .env local y no sincroniza con el backend.",
    )
    return parser.parse_args()


def resolve_env_file(env_file_argument: str) -> Path:
    """Resuelve ruta absoluta del archivo .env."""
    candidate = Path(env_file_argument)
    return candidate if candidate.is_absolute() else EDGE_ROOT / candidate


def load_edge_config(env_file_path: Path) -> EdgeServiceConfig:
    """Carga variables de entorno y construye la configuración edge."""
    load_dotenv(env_file_path, override=True)
    return EdgeServiceConfig()


def capture_reference_frame(config: EdgeServiceConfig, frame_skip: int) -> tuple[cv2.typing.MatLike, str]:
    """Obtiene un frame base desde la fuente configurada."""
    processor = VideoStreamProcessor(
        camera_index=config.video.camera_index,
        video_source=config.video.video_source,
        frame_width=config.video.frame_width,
        frame_height=config.video.frame_height,
        target_fps=config.video.fps,
        timeout_seconds=config.video.timeout_seconds,
    )

    try:
        processor.start()
        frame = None
        for _ in range(max(frame_skip, 1)):
            success, current_frame, _ = processor.read_frame()
            if success and current_frame is not None:
                frame = current_frame.copy()

        if frame is None:
            raise RuntimeError("No se pudo capturar un frame de referencia.")

        source_label = str(config.video.video_source)
        return frame, source_label
    finally:
        processor.release()


def mouse_callback(event: int, x: int, y: int, flags: int, state: RoiSelectionState) -> None:
    """Gestiona clicks para agregar y quitar puntos."""
    if event == cv2.EVENT_LBUTTONDOWN:
        state.add_point(x, y)
    elif event == cv2.EVENT_RBUTTONDOWN:
        state.remove_last_point()


def render_overlay(frame, state: RoiSelectionState, camera_id: str, queue_dwell_seconds: float, max_allowed_wait_seconds: float):
    """Dibuja puntos, líneas y ayuda de uso."""
    canvas = frame.copy()
    points = state.points

    for index, point in enumerate(points):
        x, y = point
        cv2.circle(canvas, (x, y), 6, (0, 255, 255), -1)
        cv2.putText(
            canvas,
            str(index + 1),
            (x + 8, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

    if len(points) >= 2:
        polyline_points = np.array(points, dtype=np.int32)
        cv2.polylines(
            canvas,
            [polyline_points],
            isClosed=len(points) >= 3,
            color=(0, 165, 255),
            thickness=2,
        )

    overlay_lines = [
        f"Camera: {camera_id}",
        f"Permanencia minima cola: {queue_dwell_seconds:.1f}s",
        f"Espera maxima permitida: {max_allowed_wait_seconds:.1f}s",
        "Click izq: agregar punto | Click der: deshacer",
        "Teclas: c limpiar | s guardar | q salir",
    ]
    for index, line in enumerate(overlay_lines):
        cv2.putText(
            canvas,
            line,
            (10, 30 + index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    return canvas


def save_roi_to_env(env_file_path: Path, roi_polygon: list[list[int]], queue_wait_threshold: float) -> None:
    """Persiste el ROI y threshold en el archivo .env de la instancia."""
    set_key(str(env_file_path), "ROI_POLYGON", json.dumps(roi_polygon))
    set_key(str(env_file_path), "QUEUE_ROI_POLYGON", json.dumps(roi_polygon))
    set_key(str(env_file_path), "QUEUE_WAIT_THRESHOLD", str(queue_wait_threshold))


def save_roi_to_backend(config: EdgeServiceConfig, roi_polygon: list[list[int]]) -> None:
    """Sincroniza el ROI con el backend usando camera_id como llave natural."""
    client = CameraConfigClient(
        base_url=config.backend_api.base_url,
        edge_node_id=config.backend_api.edge_node_id,
        edge_api_key=config.backend_api.edge_api_key,
        token=config.backend_api.token,
        username=config.backend_api.username,
        password=config.backend_api.password,
        timeout_seconds=config.backend_api.timeout_seconds,
    )
    client.upsert_camera_profile(
        camera_id=config.mqtt.camera_id,
        roi_polygon=roi_polygon,
        queue_wait_threshold=config.mqtt.queue_wait_threshold,
        queue_dwell_seconds=config.mqtt.queue_dwell_seconds,
        queue_alert_people_threshold=config.mqtt.queue_alert_people_threshold,
        queue_alert_duration_seconds=config.mqtt.queue_alert_duration_seconds,
        max_allowed_wait_seconds=config.mqtt.max_allowed_wait_seconds,
        cashier_count=config.mqtt.cashier_count,
        service_rate_per_cashier_per_minute=config.mqtt.service_rate_per_cashier_per_minute,
        video_source=str(config.video.video_source),
    )


def main() -> None:
    """Punto de entrada del selector de ROI."""
    args = parse_args()
    env_file_path = resolve_env_file(args.env_file)
    if not env_file_path.exists():
        raise FileNotFoundError(f"No existe el archivo de configuración: {env_file_path}")

    config = load_edge_config(env_file_path)
    config.validate()

    frame, source_label = capture_reference_frame(config, frame_skip=args.frame_skip)
    state = RoiSelectionState(initial_points=config.mqtt.queue_roi_polygon or config.mqtt.roi_polygon)
    window_name = f"RetroVision ROI Selector - {config.mqtt.camera_id}"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, mouse_callback, state)

    print(f"Fuente: {source_label}")
    print(f"Camera ID: {config.mqtt.camera_id}")
    print("Click izquierdo agrega puntos. Click derecho deshace el último.")
    print("Presiona 's' para guardar, 'c' para limpiar, 'q' para salir.")

    try:
        while True:
            canvas = render_overlay(
                frame=frame,
                state=state,
                camera_id=config.mqtt.camera_id,
                queue_dwell_seconds=config.mqtt.queue_dwell_seconds,
                max_allowed_wait_seconds=config.mqtt.max_allowed_wait_seconds,
            )
            cv2.imshow(window_name, canvas)
            key = cv2.waitKey(30) & 0xFF

            if key == ord("c"):
                state.clear()
            elif key == ord("s"):
                if len(state.points) < 3:
                    print("Necesitas al menos 3 puntos para guardar el ROI.")
                    continue

                save_roi_to_env(
                    env_file_path=env_file_path,
                    roi_polygon=state.points,
                    queue_wait_threshold=config.mqtt.queue_wait_threshold,
                )
                print(f"ROI guardado en {env_file_path.name}: {json.dumps(state.points)}")

                if args.no_backend_sync:
                    print("Sincronización con backend omitida por --no-backend-sync.")
                else:
                    save_roi_to_backend(config, state.points)
                    print("ROI sincronizado en backend por camera_id.")
                break
            elif key == ord("q"):
                print("Salida sin guardar cambios.")
                break
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
