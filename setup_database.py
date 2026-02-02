
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# --- Database Configuration ---
# Make sure your PostgreSQL server is running before executing this script.
# These settings should match your PostgreSQL setup and the config.py file.
DB_CONFIG = {
    "user": "postgres",
    "password": "123456",  # The password you set during PostgreSQL installation
    "host": "localhost",
    "port": "5432"
}
DB_NAME = "gudang"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_database_and_tables():
    """
    Connects to the PostgreSQL server, creates the database if it doesn't exist,
    and then creates the necessary tables within that database.
    """
    conn = None
    try:
        # --- 1. Connect to the default 'postgres' database to create our new database ---
        logging.info("Connecting to the default PostgreSQL server...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # --- 2. Check if the target database exists ---
        cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [DB_NAME])
        exists = cursor.fetchone()

        # --- 3. If it doesn't exist, create it ---
        if not exists:
            logging.info(f"Database '{DB_NAME}' not found. Creating it now...")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            logging.info(f"Database '{DB_NAME}' created successfully.")
        else:
            logging.info(f"Database '{DB_NAME}' already exists.")

        cursor.close()
        conn.close()

        # --- 4. Connect to the newly created 'gudang' database ---
        logging.info(f"Connecting to database '{DB_NAME}'...")
        conn = psycopg2.connect(**DB_CONFIG, dbname=DB_NAME)
        cursor = conn.cursor()

        # --- 5. Define and create tables ---
        tables_to_create = {
            "barang": """
                CREATE TABLE IF NOT EXISTS barang (
                    id SERIAL PRIMARY KEY,
                    nama_barang TEXT NOT NULL,
                    jumlah INTEGER NOT NULL CHECK (jumlah >= 0),
                    lemari TEXT NOT NULL,
                    lokasi TEXT NOT NULL,
                    UNIQUE(nama_barang, lemari, lokasi)
                );
            """,
            "history_barang": """
                CREATE TABLE IF NOT EXISTS history_barang (
                    id SERIAL PRIMARY KEY,
                    nama_barang TEXT,
                    jumlah INTEGER,
                    lemari TEXT,
                    lokasi TEXT,
                    aksi TEXT,
                    username TEXT,
                    waktu TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
            """,
            "history_login": """
                CREATE TABLE IF NOT EXISTS history_login (
                    id SERIAL PRIMARY KEY,
                    username TEXT,
                    aksi TEXT,
                    waktu TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """
        }

        for table_name, creation_command in tables_to_create.items():
            logging.info(f"Creating table '{table_name}' if it doesn't exist...")
            cursor.execute(creation_command)

        conn.commit()
        logging.info("All tables have been successfully created or verified.")

    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
        logging.error("Please ensure your PostgreSQL server is running and the credentials in this script are correct.")

    finally:
        if conn:
            cursor.close()
            conn.close()
            logging.info("Database connection closed.")

if __name__ == '__main__':
    create_database_and_tables()
