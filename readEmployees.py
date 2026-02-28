DEBUG_PRINTS = True

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

    MODEL_ID = "gemini-2.5-flash"
except Exception as e:
    print(f"Gemini functionality could not be imported!: {e}")
    geminiWorks = False
    if DEBUG_PRINTS: print("Gemini Disabled!")


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

            
            if "id" in reader.fieldnames and "firstName" in reader.fieldnames and "lastNames" in reader.fieldnames and False:
                pass
            else:
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
                        if DEBUG_PRINTS: print("Before response")
                        response = client.models.generate_content(contents= prompt + str(reader.fieldnames), model=MODEL_ID)
                    except errors.ClientError as e:
                        if DEBUG_PRINTS: print(f"Gemini error code: {e}")
                        if e.code == 429 and attempts:
                            if "limit: 0" in str(e):
                                attempts = 0
                                if DEBUG_PRINTS:
                                    print("Gemini limit exceeded!")
                            if attempts:
                                attempts -= 1
                                try:
                                    waitTime = int(float(str(e).split("retry in ")[1].split("s")[0])) + 1

                                except:
                                    waitTime = 10
                                    
                                # If the wait time is long, Gemini is disabled so the program does not freeze
                                if waitTime > 67:
                                    waitTime = 0
                                    attempts = 0

                                if DEBUG_PRINTS:
                                    print(f"Attempts remaining: {attempts}")
                                    print(f"Wait Time: {waitTime}")

                                time.sleep(waitTime)
                        else: 
                            geminiWorks = False
                            attempts = 0
                            if DEBUG_PRINTS: 
                                print(f"Gemini Disabled!")
                        
                    except Exception as e:
                        if DEBUG_PRINTS: print(e)
                        geminiWorks = False
                        attempts = 0
                        if DEBUG_PRINTS: 
                            print(f"Gemini Disabled!")

                
                
                if geminiWorks and response:  
                    if DEBUG_PRINTS: print("Reponse:")   
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
                if DEBUG_PRINTS: print(f"Duplicate ID!: {row["id"]}")
            else:
                if row["id"]:
                    employees[row["id"]] = Employee.Employee(row["firstName"], row["lastName"], row["id"])
                else:
                    if DEBUG_PRINTS: print("Missing ID!")


if __name__ == "__main__":
    formatReadEmployeeData("EmployeeData.csv")