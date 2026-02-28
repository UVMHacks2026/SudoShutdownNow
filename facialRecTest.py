import os
from google import genai
from PIL import Image
# Initialize the client (Make sure your GEMINI_API_KEY environment variable is set)
# export GEMINI_API_KEY="your-api-key-here"
client = genai.Client(api_key="AIzaSyCr4liDQWEeFor_PT5Vr-7KkmRtMZvyL1Y")

# Load the image you want to analyze
# Replace 'faces.jpg' with the path to your image file
image = Image.open('faces.jpg')

# Define your prompt focusing on analysis, not recognition
prompt = "Analyze the faces in this image and provide the following:\n1. How many people are in the image?\n2. What are their general expressions or emotions?\n3. Describe any notable facial features or accessories (like glasses, beards, etc.)\nDo not attempt to identify who they are."

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[image, prompt]
)

print(response.text)