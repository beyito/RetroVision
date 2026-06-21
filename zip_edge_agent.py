import os
import zipfile

def create_edge_zip():
    # Use relative paths based on the location of this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(base_dir, "retrovision_edge")
    output_dir = os.path.join(base_dir, "backend", "alerts_api", "static")
    output_zip = os.path.join(output_dir, "retrovision_edge.zip")
    
    # Ensure static directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Files and folders to exclude
    exclude_folders = {"venv", "__pycache__", ".git", ".idea", "logs", "alerts"}
    exclude_files = {
        ".env", 
        ".env.webcam", 
        ".env.prueba", 
        "yolov8m.pt", 
        "yolov8s.pt", 
        "yolov8n.pt"
    }
    
    print(f"Creating ZIP archive from: {source_dir}...")
    print(f"Output ZIP path: {output_zip}")
    
    count = 0
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to skip excluded folders
            dirs[:] = [d for d in dirs if d not in exclude_folders]
            
            for file in files:
                if file in exclude_files:
                    continue
                
                # Check for other large model weights not explicitly listed
                if file.endswith(".pt") and file != "best.pt":
                    continue
                    
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                
                zipf.write(full_path, rel_path)
                count += 1
                
    print(f"ZIP created successfully with {count} files!")
    size_mb = os.path.getsize(output_zip) / (1024 * 1024)
    print(f"ZIP file size: {size_mb:.2f} MB")

if __name__ == "__main__":
    create_edge_zip()
