import psycopg2
import logging
import json
import numpy as np

# Configure logging (set to ERROR to keep the CLI clean)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# --- LOAD SECRETS ---
try:
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
        
    DATABASE_URL = secrets.get("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ Error: Missing DATABASE_URL in secrets.json!")
        exit(1)
        
except FileNotFoundError:
    print("❌ Error: secrets.json not found in the root directory! Please create it.")
    exit(1)


def get_db_connection():
    """Helper to get a database connection."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None


def setup_users_table():
    """Connect to PostgreSQL and create the employees table with the requested schema."""
    conn = get_db_connection()
    if not conn: return

    try:
        cursor = conn.cursor()
        
        print("\n⏳ Setting up database tables...")

        # Create the table matching your exact requirements
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,                     -- Internal DB ID
            employee_id VARCHAR(50) UNIQUE NOT NULL,   -- The Employee's ID (e.g., 'EMP123')
            first_name VARCHAR(100) NOT NULL,          -- Employee First Name
            last_name VARCHAR(100) NOT NULL,           -- Employee Last Name
            email VARCHAR(255) UNIQUE NOT NULL,        -- Employee Email
            image_id VARCHAR(255),                     -- ID/Path to where the picture is stored
            embedding BYTEA NOT NULL,                  -- InsightFace embedding array (Required for facial rec)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        
        # Create indexes for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_emp_id ON users(employee_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        
        # Commit the changes
        conn.commit()
        print("✅ Employee database table successfully verified/created!")

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def add_new_employee():
    """Interactive prompt to add a new employee to the database."""
    print("\n--- 📝 ADD NEW EMPLOYEE ---")
    employee_id = input("Enter Employee ID (e.g., EMP001): ").strip()
    first_name = input("Enter First Name: ").strip()
    last_name = input("Enter Last Name: ").strip()
    email = input("Enter Email Address: ").strip()
    image_id = input("Enter Image ID (e.g., img_001.jpg): ").strip()
    
    # We need a dummy embedding to save the row, because the facial recognition 
    dummy_embedding = np.zeros(512, dtype=np.float32).tobytes()

    conn = get_db_connection()
    if not conn: return

    try:
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO users (employee_id, first_name, last_name, email, image_id, embedding)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            employee_id, 
            first_name, 
            last_name, 
            email, 
            image_id, 
            psycopg2.Binary(dummy_embedding)
        ))
        conn.commit()
        
        print(f"\n✅ Successfully added {first_name} {last_name} ({employee_id}) to the database!")
        
    except psycopg2.IntegrityError as e:
        conn.rollback()
        # Handle cases where the email or employee ID already exists
        if "users_employee_id_key" in str(e):
            print(f"\n❌ Error: Employee ID '{employee_id}' already exists!")
        elif "users_email_key" in str(e):
            print(f"\n❌ Error: Email '{email}' already exists!")
        else:
            print(f"\n❌ Integrity Error: {e}")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"\n❌ Database error: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def view_all_employees():
    """Fetches and displays all employees currently in the database."""
    conn = get_db_connection()
    if not conn: return

    try:
        cursor = conn.cursor()
        
        # Select all relevant text fields (ignoring massive byte array)
        cursor.execute("""
            SELECT employee_id, first_name, last_name, email, image_id 
            FROM users 
            ORDER BY created_at DESC;
        """)
        
        employees = cursor.fetchall()
        
        if not employees:
            print("\n⚠️ The database is currently empty. No employees found.")
            return

        print("\n--- 👥 REGISTERED EMPLOYEES ---")
        # Header formatting
        print(f"{'EMP ID':<10} | {'FIRST NAME':<12} | {'LAST NAME':<12} | {'EMAIL':<22} | {'IMAGE ID':<15}")
        print("-" * 80)
        
        # Row formatting
        for emp in employees:
            emp_id, fname, lname, email, img_id = emp
            
            # Handle cases where image_id might be None
            img_id_display = img_id if img_id else "None"
            
            print(f"{emp_id:<10} | {fname:<12} | {lname:<12} | {email:<22} | {img_id_display:<15}")
            
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
