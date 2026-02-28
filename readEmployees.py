import csv

import Employee

Employees = {}

with open("EmployeeData.csv", newline="") as csvFile:
    reader = csv.DictReader(csvFile)
    for row in reader:
        print(row["firstName"])