from fastapi import FastAPI
import numpy as np # for storing face encodings


app = FastAPI()

@app.get("/")

def root():
    return {"message": "Hello World"}

def get_data():
    #TODO: Implement data retrieval logic here
    
    # Get the employee
    return {"data": "This is some data"}

def process_data(data):
    pass