import csv
import os

# Path to the local CSV file
CSV_FILE_PATH = "EmployeeData.csv"

def append_to_csv(first_name, last_name, employee_id, image_id, email, shifts):
    # Check if the file already exists so we know whether to write the header row
    file_exists = os.path.exists(CSV_FILE_PATH)
    
    try:
        if file_exists and os.path.getsize(CSV_FILE_PATH) > 0:
            with open(CSV_FILE_PATH, 'rb') as f:
                f.seek(-1, os.SEEK_END)
                if f.read() != b'\n':
                    with open(CSV_FILE_PATH, 'a') as text_file:
                        text_file.write('\n')
        
        # Open in 'a' (append) mode
        with open(CSV_FILE_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Write header if file is completely new
            if not file_exists:
                writer.writerow(['firstName', 'lastName', 'id', 'imageId', 'email', 'shifts'])
            
            # Write the new employee data row 
            writer.writerow([first_name, last_name, employee_id, image_id, email, shifts])
            print(f"✅ Appended {first_name} {last_name} ({employee_id}) to a new line in {CSV_FILE_PATH}")
            return True
            
    except Exception as e:
        print(f"❌ Failed to write to {CSV_FILE_PATH}: {e}")
        return False


def add_new_employee():
    print("\n--- 📝 ADD NEW EMPLOYEE ---")
    first_name = input("Enter First Name: ").strip()
    last_name = input("Enter Last Name: ").strip()
    employee_id = input("Enter Employee ID (e.g., EMP1011): ").strip()
    image_id = input("Enter Image ID (e.g., 11): ").strip()
    email = input("Enter Email Address: ").strip()
    shifts = input("Enter Shifts (e.g., Mon-Wed, 9-5): ").strip()
    
    # Save directly to CSV
    append_to_csv(first_name, last_name, employee_id, image_id, email, shifts)


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
            
            # Use safe indexing in case the header is malformed
            h_fname = header[0] if len(header) > 0 else 'firstName'
            h_lname = header[1] if len(header) > 1 else 'lastName'
            h_id    = header[2] if len(header) > 2 else 'id'
            h_img   = header[3] if len(header) > 3 else 'imageId'
            h_email = header[4] if len(header) > 4 else 'email'
            h_shift = header[5] if len(header) > 5 else 'shifts'

            print(f"{h_id:<10} | {h_fname:<15} | {h_lname:<15} | {h_email:<25} | {h_img:<10} | {h_shift:<15}")
            print("-" * 100)
            
            # Print each employee row
            for row in rows[1:]:
                # Check to make sure the row has enough columns to prevent index errors
                if len(row) >= 6:
                    fname, lname, emp_id, img_id, email, shifts = row[0], row[1], row[2], row[3], row[4], row[5]
                    print(f"{emp_id:<10} | {fname:<15} | {lname:<15} | {email:<25} | {img_id:<10} | {shifts:<15}")
                elif len(row) >= 5: # Some older rows in your CSV only have 5 columns!
                    fname, lname, emp_id, img_id, email = row[0], row[1], row[2], row[3], row[4]
                    print(f"{emp_id:<10} | {fname:<15} | {lname:<15} | {email:<25} | {img_id:<10} | N/A")
                else:
                    # Skip empty rows that might occur
                    if len(row) > 0:
                        print(f"⚠️ Malformed row: {row}")
                    
    except Exception as e:
        print(f"❌ Failed to read {CSV_FILE_PATH}: {e}")


# --- INTERACTIVE TERMINAL APP ---
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🛠️  LOCAL CSV EMPLOYEE MANAGER 🛠️")
    print("="*50)
    
    while True:
        print("\nSelect an action:")
        print("1. Add a New Employee to CSV")
        print("2. View All Employees in CSV")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1/2/3): ").strip()
        
        if choice == '1':
            add_new_employee()
        elif choice == '2':
            view_all_employees()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


# --- INTERACTIVE TERMINAL APP ---
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🛠️  LOCAL CSV EMPLOYEE MANAGER 🛠️")
    print("="*50)
    
    while True:
        print("\nSelect an action:")
        print("1. Add a New Employee to CSV")
        print("2. View All Employees in CSV")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1/2/3): ").strip()
        
        if choice == '1':
            add_new_employee()
        elif choice == '2':
            view_all_employees()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
