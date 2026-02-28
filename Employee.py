import dotenv

class Employee:
    # Constructor for Employee Object
    def __init__(self, firstName, lastName, id, image_id):
        self.firstName = firstName
        self.lastName = lastName
        self.id = id
        self.image_id = image_id
    def __str__(self):
        return f"{self.firstName} {self.lastName} (Payroll: {self.id}, Face: {self.image_id})"
