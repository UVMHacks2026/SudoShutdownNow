import dotenv

class Employee:
    # Constructor for Employee Object
    def __init__(self, firstName, lastName, id, imageId, email):
        self.firstName = firstName
        self.lastName = lastName
        self.id = id
        self.imageId = imageId
        self.email = email
        self.shifts = 

    def getFirstName(self):
        return self.firstName
    
    def setFirstName(self, firstName):
        self.firstName = firstName
 
    def getLastName(self):
        return self.lastName   

    def setLastName(self, lastName):
        self.lastName = lastName
    
    def getId(self):
        return self.id

    def getImageId(self):
        return self.imageId
    
    def getEmail(self):
        return self.email

    def setEmail(self, email):
        self.email = email
    
    def __str__(self):
        return f"{self.firstName} {self.lastName} (Payroll: {self.id}, Face: {self.imageId}), Email: {self.email}"
