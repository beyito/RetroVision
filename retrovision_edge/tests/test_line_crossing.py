import unittest
from unittest.mock import patch
from edge_service.detection_pipeline import DetectionPipeline

class TestLineCrossingMath(unittest.TestCase):
    @patch('edge_service.detection_pipeline.DetectionPipeline._initialize_pipeline')
    def setUp(self, mock_init):
        # Create a pipeline instance with dummy parameters
        self.pipeline = DetectionPipeline(
            camera_index=0,
            video_source="dummy",
            counting_line=[[0.1, 0.5], [0.9, 0.5]], # Horizontal line
            counting_line_direction="forward"
        )

    def test_ccw(self):
        A = (0, 0)
        B = (10, 0)
        C = (5, 5) # CCW
        D = (5, -5) # CW
        self.assertTrue(self.pipeline._ccw(A, B, C))
        self.assertFalse(self.pipeline._ccw(A, B, D))

    def test_segments_intersect(self):
        # Segment 1: (0, 5) to (10, 5)
        # Segment 2: (5, 0) to (5, 10) -> Should intersect
        self.assertTrue(self.pipeline._segments_intersect((0, 5), (10, 5), (5, 0), (5, 10)))
        
        # Segment 3: (5, 0) to (5, 4) -> Should NOT intersect
        self.assertFalse(self.pipeline._segments_intersect((0, 5), (10, 5), (5, 0), (5, 4)))

    def test_crossing_logic_simulation(self):
        # Simulate tracking crossing the line
        # Frame size = 1000 x 1000 for simplicity
        w, h = 1000, 1000
        P1_abs = (int(self.pipeline.counting_line[0][0] * w), int(self.pipeline.counting_line[0][1] * h))
        P2_abs = (int(self.pipeline.counting_line[1][0] * w), int(self.pipeline.counting_line[1][1] * h))
        
        # P1_abs = (100, 500), P2_abs = (900, 500)
        self.assertEqual(P1_abs, (100, 500))
        self.assertEqual(P2_abs, (900, 500))
        
        # Moving downwards: (500, 400) -> (500, 600)
        self.assertTrue(self.pipeline._segments_intersect((500, 400), (500, 600), P1_abs, P2_abs))

if __name__ == "__main__":
    unittest.main()
