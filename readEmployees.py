import csv

import Employee

employees = {}

def readEmployees(fileName):
    try:
        with open(fileName, newline="") as csvFile:
            reader = csv.DictReader(csvFile)
            for row in reader:
                if row["id"] in employees:
                    print(f"Duplicate ID: {row["id"]}")
                else:
                    employees[row["id"]] = Employee.Employee(row["firstName"], row["lastName"], row["id"])
    except FileNotFoundError:
        print(f"Could not load the file: {fileName}")
    except Exception as e:
        print(f"An unexpected error has occured!: {e}")

if __name__ == "__main__":
    readEmployees("EmployeeData.csv")