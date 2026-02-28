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

            # Checks if the fields are formatted correctly            
            if not ("id" in reader.fieldnames and "firstName" in reader.fieldnames and "lastNames" in reader.fieldnames):
                attempts = 4
                response = ""
                while attempts:
                    try:
                        # The fields are supposes to look like ['firstName', 'lastName', 'id']
                        prompt = """
                                    You are helping to rename the headers of a csv file in python.
                                    Rename different versions of these field to firstName, lastName, id.
                                    Keep fields in their original order.
                                    fields are case sensitive in camelCase, that means d in id is lowercase.
                                    An example is ['imageId', 'otherfield', 'firstName', 'lastName', 'id'].
                                    If there are clear first name and last name fields, Your response should be: firstName, lastName, id, otherField, imageId|noSplit.
                                    If the data only has one name field (first name and last name) combined, rename the field to firstName,
                                    Your response should be: firstName, id, otherField, imageId|Split.
                                    Do not include any explanation, only the names in the correct order.
                                    The input header is:
                                """
                        if DEBUG_PRINTS: print("Before response")
                        response = client.models.generate_content(contents= prompt + str(reader.fieldnames), model=MODEL_ID)
                        attempts = 0
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
                    if DEBUG_PRINTS: print(response.text.strip())
                    reader.fieldnames = [name.strip() for name in response.text.strip().split("|")[0].split(",")]
            splitName = True if response.text.strip().split("|")[1] == "Split" else False

            return loadEmployees(reader, splitName)

                    

    except FileNotFoundError:
        print(f"Could not load the file: {fileName}")
    except Exception as e:
        print(f"An unexpected error has occured!: {e}")
    
def readEmployeeData(fileName):
    try:
        with open(fileName, newline="") as csvFile:
            reader = csv.DictReader(csvFile)
            return loadEmployees(reader)
    except FileNotFoundError:
        print(f"Could not load the file: {fileName}")
    except Exception as e:
        print(f"An unexpected error has occured!: {e}")

def loadEmployees(reader, splitName=False):
    employees = {}

    for row in reader:
        if row["id"] in employees:
            if DEBUG_PRINTS: print(f"Duplicate ID!: {row["id"]}")
        else:
            if row["id"]:
                if splitName:
                    name = row["firstName"].split(" ")
                    if len(name) < 2:
                        firstName = ""
                        lastName = name[0]
                    else:
                        firstName = name[0]
                        lastName = name[1]

                    employees[row["id"]] = Employee.Employee(firstName, lastName, row["id"], row["imageId"])
                else:
                    employees[row["id"]] = Employee.Employee(row["firstName"], row["lastName"], row["id"], row["imageId"])
            else:
                if DEBUG_PRINTS: print("Missing ID!")
    return employees
        
if __name__ == "__main__":
    employees = formatReadEmployeeData("EmployeeDataTest.csv")

    if employees:
        for employee in employees:
            print(employees[employee])