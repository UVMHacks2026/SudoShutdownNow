import csv
import Employee
import time
# Imports and configures Gemini. 
# If this can't be done other functions will work but Gemini based functions will be disabled.
geminiWorks = True
try:
    import google.genai as genai
    from google.genai import errors

    # Not part of Gemini, but only used by Gemini based functions.
    # import pandas as pd
    import os
    from dotenv import load_dotenv

    # Loads API key from .env file
    load_dotenv()
    apiKey = os.getenv("GEMINI_API_KEY")
    if apiKey:
        client = genai.Client(api_key = apiKey)
    else:
        print("Missing API key!")
        geminiWorks = False
        pass

    MODEL_ID = "gemini-2.0-flash"
except Exception as e:
    print(f"Gemini functionality could not be imported!: {e}")
    geminiWorks = False


employees = {}

"""
Formats the headers of an employee data csv file
input: File modified

"""
def formatReadEmployeeData(fileName):
    global geminiWorks

    if not geminiWorks:
        print("This function can't be used as Gemini could not be imported!")
        return 
    try:
        with open(fileName, newline="") as csvFile:
            reader = csv.DictReader(csvFile)
            print(reader.fieldnames)

            attempts = 4
            response = ""
            while attempts:
                try:
                    # The fields are supposes to look like ['firstName', 'lastName', 'id']
                    prompt = """
                                You are helping to rename the headers of a csv file in python.
                                Rename different versions of these field to firstName, lastName, id.
                                Keep fields in their original order.
                                An example is ['otherfield', 'firstName', 'lastName', 'id'].
                                The input header is:
                             """
                    response = client.models.generate_content(contents= prompt + str(reader.fieldnames), model=MODEL_ID)
                except errors.ClientError as e:
                    if e.code == 429 and attempts:
                        if attempts:
                            attempts -= 1
                            print(f"An unexpected error has occured!: {e}")
                            print(f"Attempts remaining: {attempts}")
                            try:
                                wait_time = int(float(str(e).split("retry in ")[1].split("s")[0]))
                            except:
                                wait_time = 10
                            time.sleep(11)
                    else: geminiWorks = False
            
            if geminiWorks and response:     
                print(response)

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