import base64

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
        
        # Convert image to JPEG format and encode as base64
        jpeg_buffer = io.BytesIO()
        image.convert("RGB").save(jpeg_buffer, format="JPEG")
        jpeg_buffer.seek(0)
        image_base64 = base64.b64encode(jpeg_buffer.getvalue()).decode("utf-8")
    
        # Call your facial recognition function here with the image
        
        

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "image_base64": image_base64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")