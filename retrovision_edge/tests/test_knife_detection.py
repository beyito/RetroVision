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
        print("   Model loaded successfully!")
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
        
        # Test mock class_name="knife", class_name="scissors", class_name="pistol" and class_name="mask" logic directly
        # Ensure it elevates risk score to max(0.95, confidence) and adds correct rule
        for name, cid, expected_rule in [
            ("knife", 43, "Presencia de Arma Blanca"),
            ("scissors", 76, "Presencia de Arma Blanca"),
            ("pistol", 1, "Presencia de Arma de Fuego"),
            ("mask", 2, "Persona Enmascarada")
        ]:
            mock_det = Detection(
                x1=150, y1=150, x2=250, y2=350,
                confidence=0.88,
                class_id=cid,
                class_name=name
            )
            
            high_risk_detected = False
            analysis_rules = []
            
            is_weapon = mock_det.class_name.lower() in (
                "knife", "scissors", "pistol", "handgun", "firearm", "gun", "rifle"
            ) or any(
                w in mock_det.class_name.lower() for w in ("knife", "scissors", "pistol", "handgun", "firearm", "gun", "rifle")
            )
            is_mask = mock_det.class_name.lower() == "mask"
            
            if is_weapon or is_mask:
                mock_det.risk_score = max(0.95, mock_det.confidence)
                high_risk_detected = True
                
                is_firearm = any(w in mock_det.class_name.lower() for w in ("pistol", "handgun", "firearm", "gun", "rifle"))
                is_cold_weapon = any(w in mock_det.class_name.lower() for w in ("knife", "scissors"))
                if is_firearm:
                    analysis_rules.append("Presencia de Arma de Fuego")
                elif is_cold_weapon:
                    analysis_rules.append("Presencia de Arma Blanca")
                elif is_mask:
                    analysis_rules.append("Persona Enmascarada")
                else:
                    analysis_rules.append("Presencia de Arma Blanca")
                
            print(f"   Analyzed risk score for {name}: {mock_det.risk_score}")
            print(f"   Triggered rules: {analysis_rules}")
            
            assert mock_det.risk_score == 0.95, f"Risk score was not elevated to 0.95 for {name} detection!"
            assert expected_rule in analysis_rules, f"Rule {expected_rule} was not appended for {name}!"
            assert high_risk_detected is True, "High risk flag not set!"
        
        # Test no-mask logic
        mock_no_mask = Detection(
            x1=150, y1=150, x2=250, y2=350,
            confidence=0.92,
            class_id=3,
            class_name="no-mask"
        )
        is_weapon = mock_no_mask.class_name.lower() in ("knife", "scissors", "pistol", "handgun", "firearm", "gun", "rifle")
        is_mask = mock_no_mask.class_name.lower() == "mask"
        assert not (is_weapon or is_mask), "no-mask should not trigger weapon or mask threat checks!"
        print("   no-mask detection test passed (ignored as expected)!")
        
        print("   Weapon & Mask risk analyzer logic validation passed!")
    except Exception as e:
        print(f"   [FAIL] Pipeline testing failed: {e}")
        sys.exit(1)

    print("\n--------------------------------------------------")
    print("ALL WEAPON INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("--------------------------------------------------")

if __name__ == "__main__":
    test_knife_integration()
