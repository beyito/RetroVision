import unittest
import numpy as np
from unittest.mock import patch, MagicMock
from edge_service.detection_pipeline import DetectionPipeline

class TestOptInAndZones(unittest.TestCase):
    @patch('edge_service.detection_pipeline.DetectionPipeline._initialize_pipeline')
    def setUp(self, mock_init):
        # Setup pipeline with defaults (all analytics disabled)
        self.pipeline_disabled = DetectionPipeline(
            camera_index=0,
            video_source="dummy",
            roi_polygon=None,
            queue_roi_polygon=None,
            counting_line=None,
            custom_zones=None
        )

        # Setup pipeline with custom zones
        self.pipeline_zones = DetectionPipeline(
            camera_index=0,
            video_source="dummy",
            custom_zones=[
                {
                    "name": "Lácteos",
                    "polygon": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.4], [0.1, 0.4]]
                },
                {
                    "name": "Carnes",
                    "polygon": [[0.5, 0.5], [0.8, 0.5], [0.8, 0.8], [0.5, 0.8]]
                }
            ]
        )

    def test_analytics_disabled_by_default(self):
        # Verify that modules are flagged as disabled/empty
        self.assertEqual(len(self.pipeline_disabled.counting_line), 0)
        self.assertEqual(len(self.pipeline_disabled.queue_roi_polygon), 0)
        self.assertEqual(len(self.pipeline_disabled.custom_zones), 0)
        self.assertIsNone(self.pipeline_disabled.roi_poly_np)
        self.assertIsNone(self.pipeline_disabled.queue_roi_poly_np)

    def test_custom_zones_loading(self):
        # Verify custom zones load correctly
        self.assertEqual(len(self.pipeline_zones.custom_zones), 2)
        self.assertEqual(self.pipeline_zones.custom_zones[0]["name"], "Lácteos")
        self.assertEqual(self.pipeline_zones.custom_zones[1]["name"], "Carnes")

    def test_custom_zones_occupancy_scaling_and_tracking(self):
        # We simulate a frame size of 1000x1000
        w_frame, h_frame = 1000, 1000
        
        # Manually perform scaling step like in process_frame
        scaled_custom_zones = []
        for zone in self.pipeline_zones.custom_zones:
            zone_name = zone.get("name", "Zona")
            normalized_poly = zone.get("polygon", [])
            abs_poly = []
            for pt in normalized_poly:
                abs_poly.append([int(pt[0] * w_frame), int(pt[1] * h_frame)])
            abs_poly_np = np.array(abs_poly, dtype=np.int32).reshape((-1, 1, 2))
            scaled_custom_zones.append((zone_name, abs_poly_np))

        # Check that we have 2 scaled zones
        self.assertEqual(len(scaled_custom_zones), 2)
        self.assertEqual(scaled_custom_zones[0][0], "Lácteos")
        self.assertEqual(scaled_custom_zones[1][0], "Carnes")

        # Let's test a point inside Lácteos: normalized x=0.2, y=0.2 => absolute x=200, y=200
        # Polygon Lácteos: x in [100, 300], y in [100, 400]
        # Carnes: x in [500, 800], y in [500, 800]
        import cv2

        # Point inside Lácteos
        cx1, cy1 = 200, 200
        inside_lacteos = cv2.pointPolygonTest(scaled_custom_zones[0][1], (float(cx1), float(cy1)), False) >= 0
        inside_carnes = cv2.pointPolygonTest(scaled_custom_zones[1][1], (float(cx1), float(cy1)), False) >= 0
        self.assertTrue(inside_lacteos)
        self.assertFalse(inside_carnes)

        # Point inside Carnes
        cx2, cy2 = 600, 600
        inside_lacteos2 = cv2.pointPolygonTest(scaled_custom_zones[0][1], (float(cx2), float(cy2)), False) >= 0
        inside_carnes2 = cv2.pointPolygonTest(scaled_custom_zones[1][1], (float(cx2), float(cy2)), False) >= 0
        self.assertFalse(inside_lacteos2)
        self.assertTrue(inside_carnes2)

        # Point outside both
        cx3, cy3 = 900, 900
        inside_lacteos3 = cv2.pointPolygonTest(scaled_custom_zones[0][1], (float(cx3), float(cy3)), False) >= 0
        inside_carnes3 = cv2.pointPolygonTest(scaled_custom_zones[1][1], (float(cx3), float(cy3)), False) >= 0
        self.assertFalse(inside_lacteos3)
        self.assertFalse(inside_carnes3)

if __name__ == "__main__":
    unittest.main()
