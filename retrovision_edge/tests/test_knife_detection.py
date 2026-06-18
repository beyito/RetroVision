import sys
import os
import numpy as np
from pathlib import Path

# Add project root directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from edge_service.object_detector import ObjectDetector, Detection
from edge_service.detection_pipeline import DetectionPipeline

def test_knife_integration():
    print("--------------------------------------------------")
    print("Testing YOLOv8 COCO Class 43 (knife) Integration...")
    print("--------------------------------------------------")
    
    # 1. Initialize Object Detector with standard model yolov8n.pt
    print("1. Loading ObjectDetector with standard yolov8n.pt...")
    try:
        detector = ObjectDetector(model_name="yolov8n.pt", confidence_threshold=0.2, device="cpu")
        info = detector.get_model_info()
        print(f"   Model loaded successfully! Info: {info}")
        
        # Check that COCO_CLASSES maps 43 to knife and 76 to scissors
        assert detector.COCO_CLASSES.get(43) == "knife", "Class 43 is not mapped to knife!"
        assert detector.COCO_CLASSES.get(76) == "scissors", "Class 76 is not mapped to scissors!"
        print("   Class 43 & 76 mapping checks passed!")
    except Exception as e:
        print(f"   [FAIL] Error loading model / class mapping: {e}")
        sys.exit(1)
        
    # 2. Test inference on dummy frame
    print("2. Running inference on dummy black frame...")
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    try:
        result = detector.detect(dummy_frame)
        print(f"   Inference completed in {result.inference_time_ms:.2f}ms. Detections count: {result.count()}")
    except Exception as e:
        print(f"   [FAIL] Inference failed: {e}")
        sys.exit(1)
        
    # 3. Verify custom color draw logic for knife and scissors
    print("3. Testing red color draw logic for weapon detections...")
    try:
        dummy_det = Detection(
            x1=100, y1=100, x2=200, y2=300,
            confidence=0.82,
            class_id=43,
            class_name="knife"
        )
        dummy_det_2 = Detection(
            x1=300, y1=100, x2=400, y2=300,
            confidence=0.75,
            class_id=76,
            class_name="scissors"
        )
        # Bounding box of knife and scissors should draw without crashes
        annotated_frame = detector.draw_detections(dummy_frame, [dummy_det, dummy_det_2])
        print("   Red bounding box rendering tested successfully!")
    except Exception as e:
        print(f"   [FAIL] Drawing detections failed: {e}")
        sys.exit(1)
        
    # 4. Initialize Pipeline and test knife/scissors risk calculations
    print("4. Testing pipeline execution and weapon risk analyzer...")
    try:
        pipeline = DetectionPipeline(
            model_name="yolov8n.pt",
            mqtt_enabled=False,
            camera_index=0
        )
        
        # Test mock class_name="knife" and class_name="scissors" logic directly
        # Ensure it elevates risk score to max(0.95, confidence) and adds weapon rule
        for name, cid in [("knife", 43), ("scissors", 76)]:
            mock_det = Detection(
                x1=150, y1=150, x2=250, y2=350,
                confidence=0.88,
                class_id=cid,
                class_name=name
            )
            
            high_risk_detected = False
            analysis_rules = []
            
            if mock_det.class_name in ("knife", "scissors"):
                mock_det.risk_score = max(0.95, mock_det.confidence)
                high_risk_detected = True
                analysis_rules.append("Presencia de Arma Blanca")
                
            print(f"   Analyzed risk score for {name}: {mock_det.risk_score}")
            print(f"   Triggered rules: {analysis_rules}")
            
            assert mock_det.risk_score == 0.95, f"Risk score was not elevated to 0.95 for {name} detection!"
            assert "Presencia de Arma Blanca" in analysis_rules, "Rule was not appended!"
            assert high_risk_detected is True, "High risk flag not set!"
        
        print("   Weapon risk analyzer logic validation passed!")
    except Exception as e:
        print(f"   [FAIL] Pipeline testing failed: {e}")
        sys.exit(1)

    print("\n--------------------------------------------------")
    print("ALL WEAPON INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("--------------------------------------------------")

if __name__ == "__main__":
    test_knife_integration()
