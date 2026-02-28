import os
import base64
import json
from dotenv import load_dotenv
from facialRecognition.localFaceRec.secureFacialID import FacialSecuritySystem

def main():
    print("--- Local Facial Security System Test ---")
    
    # 1. Load environment variables
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    fernet_key = os.getenv("FERNET_KEY")
    
    if not database_url:
        print("Error: DATABASE_URL not found in .env")
        return
    
    # 2. Initialize System
    print("Initializing system...")
    try:
        system = FacialSecuritySystem(database_url=database_url, fernet_key=fernet_key)
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return
        
    print(f"System initialized. Authorized users: {list(system.authorized_users.keys())}")
    
    # 3. Look for a test image
    test_image_paths = ["test_image.png", "face.png", "faces.jpg", "test_ui.png"]
    found_path = None
    for path in test_image_paths:
        if os.path.exists(path):
            found_path = path
            break
            
    if not found_path:
        print("No test image found in root directory. Please provide a path.")
        # Try to find any png/jpg in root
        for f in os.listdir("."):
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                found_path = f
                break
                
    if not found_path:
        print("Error: No image files found to test.")
        return
        
    print(f"Using test image: {found_path}")
    
    # 4. Process Image
    with open(found_path, "rb") as f:
        img_data = f.read()
        b64_img = base64.b64encode(img_data).decode("utf-8")
        
    print("Processing frame...")
    result = system.process_frame(b64_img)
    
    print("\nTest Result:")
    print(json.dumps(result, indent=2))
    
    if result.get("is_employee_present"):
        print(f"\nSUCCESS: Employee '{result['employee_name']}' detected with confidence {result.get('confidence', 'N/A')}")
    else:
        print("\nINFO: No authorized employee detected in the image.")

if __name__ == "__main__":
    main()
