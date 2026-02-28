import csv
import Employee

# Imports and configures Gemini. 
# If this can't be done other functions will work but Gemini based functions will be disabled.
gemini_works = True
try:
    from google import genai

    # Not part of Gemini, but only used by Gemini based functions.
    # import pandas as pd
    import os
    from dotenv import load_dotenv

    # Loads API key from .env file
    load_dotenv()
    apiKey = os.getenv("GEMINI_API_KEY")
    if apiKey:
        genai.Client(api_key = apiKey)
    else:
        print("Missing API key!")
        gemini_works = False
        pass

    MODEL_ID = "gemini-1.5-flash"
except Exception as e:
    print(f"Gemini functionality could not be imported!: {e}")
    gemini_works = False


employees = {}

"""
Formats the headers of an employee data csv file
input: File modified

"""
def formatReadEmployeeData(fileName):
    if not gemini_works:
        print("This function can't be used as Gemini could not be imported!")
        return 
    try:
        with open(fileName, newline="") as csvFile:
            reader = csv.DictReader(csvFile)
            print(reader.fieldnames)
            loadEmployees(reader)
    except FileNotFoundError:
        print(f"Could not load the file: {fileName}")
    except Exception as e:
        print(f"An unexpected error has occured!: {e}")
    
def readEmployeeData(fileName):
    try:
        with open(fileName, newline="") as csvFile:
            reader = csv.DictReader(csvFile)
            loadEmployees(reader)
    except FileNotFoundError:
        print(f"Could not load the file: {fileName}")
    except Exception as e:
        print(f"An unexpected error has occured!: {e}")

def loadEmployees(reader):
        for row in reader:
            if row["id"] in employees:
                print(f"Duplicate ID!   : {row["id"]}")
            else:
                if row["id"]:
                    employees[row["id"]] = Employee.Employee(row["firstName"], row["lastName"], row["id"])
                else:
                    print("Missing ID!")


if __name__ == "__main__":
    formatReadEmployeeData("EmployeeData.csv")