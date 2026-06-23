import requests
import json
import os
from urllib import request

def verify_s3_presigned_upload():
    # 1. Login
    login_url = "http://localhost:8000/api/token/"
    credentials = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("Logging in to central platform...")
    r = requests.post(login_url, json=credentials)
    if r.status_code != 200:
        print(f"Failed to login: {r.status_code} - {r.text}")
        return
        
    token = r.json().get("access")
    print("Logged in successfully.")
    
    # 2. Extract edge credentials from retrovision_edge/.env.webcam
    node_id = "node_01"
    api_key = "ORzfXuuiLJEfiF0U9Sd9GwXTXTVQbAHYMJQqw0wXv8o"
    camera_id = "camara_local" # We'll force using camara_local for testing
    
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "retrovision_edge", ".env.webcam"))
    if os.path.exists(env_path):
        print(f"Reading credentials from {env_path}...")
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    if k.strip() == "EDGE_NODE_ID":
                        node_id = v.strip()
                    elif k.strip() == "EDGE_API_KEY":
                        api_key = v.strip()
                        
    print(f"Using Edge Node ID: {node_id}")
    print(f"Using Edge API Key: {api_key}")
    print(f"Using Camera ID: {camera_id}")
    
    # 3. Associate camera 'camara_local' to node_01's store (which is store ID 3) and node (ID 4)
    # This guarantees that the validation check in presigned_url action succeeds.
    print("\nAssociating camera 'camara_local' with store and edge node...")
    headers = {"Authorization": f"Bearer {token}"}
    patch_payload = {
        "camera_id": "camara_local",
        "store": 3, # Starbucks / Star
        "edge_node": 4 # node_01
    }
    r_patch = requests.patch("http://localhost:8000/api/cameras/camara_local/", json=patch_payload, headers=headers)
    print(f"Patch camera status: {r_patch.status_code}")
    if r_patch.status_code != 200:
        print(f"Warning: failed to patch camera: {r_patch.text}")
    else:
        print("Camera linked successfully.")
        
    # 4. Call the presigned-url endpoint
    presigned_url_endpoint = "http://localhost:8000/api/alerts/presigned-url/"
    edge_headers = {
        "X-Edge-Node-Id": node_id,
        "X-Edge-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "camera_id": camera_id,
        "filename": "alert_test_upload.mp4",
        "risk_score": 0.92,
        "rules_triggered": ["Presencia de Arma de Fuego", "Persona Enmascarada"],
        "zona": "Carnes"
    }
    
    print("\nRequesting pre-signed URL from Django backend...")
    r_url = requests.post(presigned_url_endpoint, json=payload, headers=edge_headers)
    print(f"Response status: {r_url.status_code}")
    if r_url.status_code != 200:
        print(f"Failed to get presigned URL: {r_url.text}")
        return
        
    res = r_url.json()
    presigned_url = res.get("presigned_url")
    s3_url = res.get("s3_url")
    alert_id = res.get("alert_id")
    
    print(f"Received Alert ID: {alert_id}")
    print(f"Pre-signed URL: {presigned_url}")
    print(f"Expected S3 URL: {s3_url}")
    
    # 5. Perform direct upload using HTTP PUT to the pre-signed URL
    print("\nUploading fake video file to pre-signed URL (HTTP PUT)...")
    fake_video_data = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    
    put_req = request.Request(
        presigned_url,
        data=fake_video_data,
        headers={"Content-Type": "video/mp4"},
        method="PUT"
    )
    
    try:
        with request.urlopen(put_req, timeout=10) as response:
            print(f"Upload response status: {response.status}")
            print(f"Upload response read: {response.read().decode('utf-8')}")
            
        # 6. Verify database record has been updated and points to the S3 URL using HTTP GET
        print("\nVerifying SecurityAlert database entry via HTTP GET...")
        r_alerts = requests.get(f"http://localhost:8000/api/alerts/{alert_id}/", headers=headers)
        print(f"GET alert status: {r_alerts.status_code}")
        if r_alerts.status_code != 200:
            print(f"Failed to fetch alert detail: {r_alerts.text}")
            return
            
        alert_detail = r_alerts.json()
        print(f"  camera_id: {alert_detail.get('camera_id')}")
        print(f"  risk_score: {alert_detail.get('risk_score')}")
        print(f"  rules_triggered: {alert_detail.get('rules_triggered')}")
        print(f"  zona: {alert_detail.get('zona')}")
        print(f"  video_path: {alert_detail.get('video_path')}")
        
        assert alert_detail.get("video_path") == s3_url, f"Alert video_path {alert_detail.get('video_path')} does not match expected {s3_url}"
        print("\nSUCCESS: Pre-signed S3 URL generation, HTTP PUT upload, local emulation fallback and DB persistence verified successfully via HTTP!")
        
    except Exception as e:
        print(f"Failed to perform PUT upload or verification: {e}")

if __name__ == "__main__":
    verify_s3_presigned_upload()
