import os
import json
from google import genai
from PIL import Image
from deepface import DeepFace


db_path = "path_to_your_database"  # where image files will be stored for recognition


# Load secrets
with open('secrets.json', 'r') as f:
    secrets = json.load(f)

# Initialize the client
client = genai.Client(api_key=secrets.get("GEMINI_API_KEY"))

# Load image to analyze
image = Image.open('faces.jpg')

# Define your prompt focusing on analysis, not recognition
prompt = "Analyze the faces in this image and provide the following:\n1. How many people are in the image?\n2. What are their general expressions or emotions?\n3. Describe any notable facial features or accessories (like glasses, beards, etc.)\nDo not attempt to identify who they are."

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[image, prompt]
)

print(response.text)


def load_image(image_path):
    # Take in imagine being sent every 4/5 secs and load it for processing
    # Sorin
    image = DeepFace.find(img_path=img, db_path="path_to_your_database")
    pass