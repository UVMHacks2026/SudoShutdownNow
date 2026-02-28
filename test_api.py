import requests
import base64
import json

# Read the faces.jpg we downloaded earlier for Gemini
with open("facialRecognition/gemeniFacialAnalysis/faces.jpg", "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

# Prepare the payload
payload = {
    "image_base64": encoded_string
}

# Send to our new FastAPI server
print("Sending Base64 JPG to Secure Facial ID API...")
response = requests.post("http://localhost:8000/analyze", json=payload)

if response.status_code == 200:
    print("\n✅ API Response (200 OK):")
    print(json.dumps(response.json(), indent=4))
else:
    print(f"\n❌ Error {response.status_code}:")
    print(response.text)
