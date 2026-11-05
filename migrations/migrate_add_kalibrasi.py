import psycopg2
import logging
from app.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migration():
    logging.info("Memulai migrasi penambahan kolom tgl_kalibrasi...")
    conn = psycopg2.connect(
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        host=Config.DB_HOST,
        port=Config.DB_PORT
    )
    cur = conn.cursor()

    # 1. Tambah kolom tgl_kalibrasi ke tabel barang dan history_barang
    logging.info("Menambahkan kolom 'tgl_kalibrasi' pada tabel barang & history_barang...")
    cur.execute("ALTER TABLE barang ADD COLUMN IF NOT EXISTS tgl_kalibrasi DATE;")
    cur.execute("ALTER TABLE history_barang ADD COLUMN IF NOT EXISTS tgl_kalibrasi DATE;")

    # 2. Update data sampel alat ukur Saguling dengan tanggal kalibrasi riil
    logging.info("Mengisi data kalibrasi sampel untuk perkakas pemeliharaan Saguling...")
    cur.execute("UPDATE barang SET tgl_kalibrasi = '2026-03-15' WHERE nama_barang ILIKE '%Fluke%';")
    cur.execute("UPDATE barang SET tgl_kalibrasi = '2026-01-10' WHERE nama_barang ILIKE '%Megger%';")
    cur.execute("UPDATE barang SET tgl_kalibrasi = '2025-08-20' WHERE nama_barang ILIKE '%Norbar%';") # Contoh Expired (> 1 tahun)
    cur.execute("UPDATE barang SET tgl_kalibrasi = '2026-02-01' WHERE nama_barang ILIKE '%Hioki%';")
    # Alat mekanik tetap NULL (tidak butuh kalibrasi)
    cur.execute("UPDATE barang SET tgl_kalibrasi = NULL WHERE nama_barang ILIKE '%Puller%' OR nama_barang ILIKE '%Tracker%';")

    conn.commit()
    cur.close()
    conn.close()
    logging.info("✅ Migrasi sukses: Kolom 'tgl_kalibrasi' berhasil ditambahkan dan data sampel diperbarui.")

if __name__ == '__main__':
    run_migration()
