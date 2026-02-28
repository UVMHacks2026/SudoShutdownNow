import csv

import Employee

employees = {}

with open("EmployeeData.csv", newline="") as csvFile:
    reader = csv.DictReader(csvFile)
    for row in reader:
        employees[row["id"]] = Employee.Employee(row["firstName"], row["lastName"], row["id"])