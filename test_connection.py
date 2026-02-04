
import psycopg2
import logging

# --- Database Configuration ---
# Use the same settings as your setup and application config.
DB_CONFIG = {
    "dbname": "gudang",
    "user": "postgres",
    "password": "123456",
    "host": "localhost",
    "port": "5432"
}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_connection():
    """
    Attempts to connect to the PostgreSQL database and prints the status.
    """
    conn = None
    try:
        logging.info(f"Attempting to connect to database '{DB_CONFIG["dbname"]}'...")
        conn = psycopg2.connect(**DB_CONFIG)
        
        # If the connection is successful, psycopg2.connect() will return a connection object.
        logging.info("----------------------------------------------------------")
        logging.info("✅ Database connection successful!")
        logging.info(f"Connected to PostgreSQL server version: {conn.server_version}")
        logging.info("----------------------------------------------------------")

    except psycopg2.OperationalError as e:
        # This error is typically for connection issues (e.g., server not running, wrong host/port/password).
        logging.error("----------------------------------------------------------")
        logging.error("❌ Database connection failed!")
        logging.error(f"Error: {e}")
        logging.error("Troubleshooting tips:")
        logging.error("1. Is the PostgreSQL server running on your machine?")
        logging.error("2. Are the host, port, username, and password in this script correct?")
        logging.error("3. Did you run the `setup_database.py` script first to create the database?")
        logging.error("----------------------------------------------------------")

    except psycopg2.Error as e:
        # For other potential psycopg2 errors.
        logging.error(f"A different database error occurred: {e}")

    finally:
        # Ensure the connection is closed if it was opened.
        if conn:
            conn.close()
            logging.info("Connection closed.")

if __name__ == '__main__':
    test_connection()
