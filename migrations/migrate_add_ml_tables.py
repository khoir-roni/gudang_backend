import psycopg2
import logging
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migration():
    logging.info("Memulai migrasi penambahan tabel ML Harvest Log & ML Model Release...")
    conn = psycopg2.connect(
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        host=Config.DB_HOST,
        port=Config.DB_PORT
    )
    cur = conn.cursor()

    # 1. Tabel ml_harvest_log
    logging.info("Membuat tabel 'ml_harvest_log'...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ml_harvest_log (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            image_path TEXT NOT NULL,
            ground_truth_label VARCHAR(150) NOT NULL,
            predicted_label VARCHAR(150),
            predicted_confidence DOUBLE PRECISION,
            uploaded_by VARCHAR(100),
            is_verified BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Tabel ml_model_release
    logging.info("Membuat tabel 'ml_model_release'...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ml_model_release (
            id SERIAL PRIMARY KEY,
            version VARCHAR(50) NOT NULL,
            model_filename VARCHAR(150) NOT NULL,
            labels_filename VARCHAR(150) NOT NULL,
            model_sha256 VARCHAR(64) NOT NULL,
            classes_count INTEGER DEFAULT 54,
            accuracy DOUBLE PRECISION,
            is_active BOOLEAN DEFAULT TRUE,
            release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Seed initial model release v1.0.0 jika belum ada
    cur.execute("SELECT COUNT(*) FROM ml_model_release WHERE version = 'v1.0.0';")
    if cur.fetchone()[0] == 0:
        logging.info("Mendaftarkan model awal v1.0.0 ke ml_model_release...")
        cur.execute("""
            INSERT INTO ml_model_release 
            (version, model_filename, labels_filename, model_sha256, classes_count, accuracy, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            'v1.0.0',
            'mobilenet_float.tflite',
            'labels.txt',
            '8e18936b4ffed883c2eabc1b088e6418fb83eda36ed2ff5c9106efbdffd1bf87',
            54,
            0.942,
            True
        ))

    conn.commit()
    cur.close()
    conn.close()
    logging.info("✅ Migrasi ML Tables sukses!")

if __name__ == '__main__':
    run_migration()
