class Employee:
    def __init__(self, firstName, lastName, id):
        self.firstName = firstName
        self.lastName = lastName
        self.id = id

    def __str__(self):
        return f"{self.firstName} {self.lastName} [{self.id}]"