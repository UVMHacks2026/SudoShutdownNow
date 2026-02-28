import csv
import os

# Path to the local CSV file
CSV_FILE_PATH = "EmployeeData.csv"

def append_to_csv(first_name, last_name, employee_id, image_id, email):
    # Check if the file already exists so we know whether to write the header row
    file_exists = os.path.exists(CSV_FILE_PATH)
    
    try:
        # Open in 'a' (append) mode. 'newline=""' prevents blank lines between rows on Windows
        with open(CSV_FILE_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Write header if file is completely new
            if not file_exists:
                writer.writerow(['firstName', 'lastName', 'id', 'imageId', 'email'])
            
            # Write the new employee data row
            writer.writerow([first_name, last_name, employee_id, image_id, email])
            print(f"✅ Appended {first_name} {last_name} ({employee_id}) to {CSV_FILE_PATH}")
            return True
            
    except Exception as e:
        print(f"❌ Failed to write to {CSV_FILE_PATH}: {e}")
        return False


def add_new_employee():
    print("\n--- 📝 ADD NEW EMPLOYEE ---")
    employee_id = input("Enter Employee ID (e.g., EMP1011): ").strip()
    first_name = input("Enter First Name: ").strip()
    last_name = input("Enter Last Name: ").strip()
    email = input("Enter Email Address: ").strip()
    image_id = input("Enter Image ID (e.g., 11): ").strip()
    
    # Save directly to CSV
    append_to_csv(first_name, last_name, employee_id, image_id, email)


def view_all_employees():
    if not os.path.exists(CSV_FILE_PATH):
        print(f"\n⚠️ The file {CSV_FILE_PATH} does not exist yet.")
        return

    try:
        with open(CSV_FILE_PATH, mode='r') as file:
            reader = csv.reader(file)
            
            # Read all rows into a list
            rows = list(reader)
            
            if len(rows) <= 1: # Only header exists or file is empty
                print(f"\n⚠️ No employee records found in {CSV_FILE_PATH}.")
                return
                
            print("\n--- 👥 REGISTERED EMPLOYEES (From CSV) ---")
            
            # Print the header row nicely formatted
            header = rows[0]
            print(f"{header[2]:<10} | {header[0]:<15} | {header[1]:<15} | {header[4]:<25} | {header[3]:<10}")
            print("-" * 85)
            
            # Print each employee row
            for row in rows[1:]:
                # Check to make sure the row has enough columns to prevent index errors
                if len(row) >= 5:
                    fname, lname, emp_id, img_id, email = row[0], row[1], row[2], row[3], row[4]
                    print(f"{emp_id:<10} | {fname:<15} | {lname:<15} | {email:<25} | {img_id:<10}")
                else:
                    print(f"Malformed row: {row}")
                    
    except Exception as e:
        print(f"❌ Failed to read {CSV_FILE_PATH}: {e}")
