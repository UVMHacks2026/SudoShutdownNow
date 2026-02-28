from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io

# Need to update to active facial recognition code, this is test for now
import facialRecTest  

app = FastAPI()

origins = [
    "http://cgswswk88cg04k4www8g8cgs.76.13.29.239.sslip.io/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        # Process the image as needed (e.g., save, analyze, etc.)
        # Call your facial recognition function here with the image
        

        return {"filename": file.filename, "content_type": file.content_type}