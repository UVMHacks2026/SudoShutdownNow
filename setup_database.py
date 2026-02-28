import psycopg2
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your provided Database URL
DATABASE_URL = "postgresql://postgres:mrAZjGkytlCIxDyYoGwGudmjvs0EssFKYwcRUar4lPitKxa5vreh7FRaOjUB6a2G@76.13.29.239:5432/postgres"

def setup_users_table():
    """Connect to PostgreSQL and create the employees table with the requested schema."""
    conn = None
    cursor = None
    try:
        # Connect to postgres DB
        logger.info(f"Connecting to database at {DATABASE_URL.split('@')[1]}...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        logger.info("Connected! Setting up tables...")

        # this will wipe the current table (ONLY USE TO RESET DB)
        # cursor.execute("DROP TABLE IF EXISTS users CASCADE;")

        # Create the table
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
        logger.info("✅ Employee database table successfully created/verified!")

    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("Database connection closed.")

if __name__ == "__main__":
    # Wait for user confirmation before executing
    print("This will create or update the 'users' table in the remote database.")
    proceed = input("Do you want to proceed? (y/n): ")
    
    if proceed.lower() in ['y', 'yes']:
        setup_users_table()
    else:
        print("Operation cancelled.")