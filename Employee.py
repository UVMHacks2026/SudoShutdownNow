import dotenv

class Employee:
    # Constructor for Employee Object
    def __init__(self, firstName, lastName, id, imageId, email):
        self.firstName = firstName
        self.lastName = lastName
        self.id = id
        self.imageId = imageId
        self.email = email

    def __str__(self):
        return f"{self.firstName} {self.lastName} (Payroll: {self.id}, Face: {self.imageId}), Email: {self.email}"
