import base64
from advancedTracking import FacialSecuritySystem

def main():
    system = FacialSecuritySystem()
    print("System initialized.")
    
    with open("../../test_image.png", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    b64_image = f"data:image/png;base64,{encoded_string}"
    
    print("Testing standard processing:")
    res = system.process_image(b64_image)
    print("Result:", res)
    
    print("\nTesting first time setup:")
    res_setup = system.process_image(b64_image, isFirstTimeSetup=True, setup_name="TestUser1")
    print("Setup Result:", res_setup)

if __name__ == "__main__":
    main()
