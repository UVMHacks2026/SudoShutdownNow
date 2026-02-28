from facialRecognition.localFaceRec.secureFacialID import FacialSecuritySystem
import base64
import json

def test_module():
    print("1. Initializing System Engine (Loading Models & DB)...")
    security_system = FacialSecuritySystem()

    # Read our test image
    with open("facialRecognition/gemeniFacialAnalysis/faces.jpg", "rb") as f:
        base64_img = base64.b64encode(f.read()).decode('utf-8')

    isFirstTimeSetup = False # Change this to test the branches
    
    if isFirstTimeSetup:
        print("\n2. EXECUTING: First Time Setup Route")
        new_employee_name = "Will_T"
        print(f"   Attempting to register {new_employee_name}...")
        
        result = security_system.register_user(base64_img, new_employee_name)
        print("   Returned Data:")
        print(json.dumps(result, indent=4))
        
    else:
        print("\n2. EXECUTING: Standard Processing Route")
        print("   Sending frame for analysis...")
        
        result = security_system.process_frame(base64_img)
        print("   Returned Data:")
        print(json.dumps(result, indent=4))

if __name__ == "__main__":
    test_module()
