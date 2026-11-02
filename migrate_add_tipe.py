import psycopg2
import logging
from app.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migration():
    logging.info("Memulai migrasi database...")
    conn = psycopg2.connect(
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        host=Config.DB_HOST,
        port=Config.DB_PORT
    )
    cur = conn.cursor()

    # 1. Pastikan kolom lemari ada di tabel barang & history_barang
    logging.info("Memeriksa kolom 'lemari'...")
    cur.execute("ALTER TABLE barang ADD COLUMN IF NOT EXISTS lemari VARCHAR(50) DEFAULT '' NOT NULL;")
    cur.execute("ALTER TABLE history_barang ADD COLUMN IF NOT EXISTS lemari VARCHAR(50) DEFAULT '' NOT NULL;")

    # 2. Tambahkan kolom tipe ('tool' vs 'material')
    logging.info("Memeriksa kolom 'tipe'...")
    cur.execute("ALTER TABLE barang ADD COLUMN IF NOT EXISTS tipe VARCHAR(20) DEFAULT 'tool' NOT NULL;")
    cur.execute("ALTER TABLE history_barang ADD COLUMN IF NOT EXISTS tipe VARCHAR(20) DEFAULT 'tool' NOT NULL;")

    # 3. Update data NULL ke default 'tool'
    cur.execute("UPDATE barang SET tipe = 'tool' WHERE tipe IS NULL;")
    cur.execute("UPDATE history_barang SET tipe = 'tool' WHERE tipe IS NULL;")

    # 4. Tambahkan beberapa contoh perkakas pemeliharaan Saguling jika belum ada
    sample_tools = [
        ("Multimeter Fluke 87V True RMS", 3, "Lemari A1", "Bengkel K&I", "tool"),
        ("Insulation Tester Megger MIT515", 1, "Lemari A2", "Bengkel K&I", "tool"),
        ("Kunci Torsi Norbar 60-300 Nm", 2, "Lemari B1", "Powerhouse B1", "tool"),
        ("Clamp Meter Hioki 3280-10F", 4, "Lemari A1", "Bengkel K&I", "tool"),
        ("Bearing Puller / Tracker SKF", 2, "Lemari B2", "Powerhouse B1", "tool"),
    ]

    sample_materials = [
        ("Kabel NYAF 1x1.5 mm Merah", 50, "Rak C1", "Gudang Material", "material"),
        ("Terminal Block Phoenix Contact", 100, "Rak C2", "Gudang Material", "material"),
        ("Isolasi Listrik 3M Scotch 33+", 20, "Rak C3", "Gudang Material", "material"),
    ]

    for nama, jml, lem, lok, tip in sample_tools + sample_materials:
        cur.execute(
            "SELECT id FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
            (nama, lem, lok)
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO barang (nama_barang, jumlah, lemari, lokasi, tipe) VALUES (%s, %s, %s, %s, %s)",
                (nama, jml, lem, lok, tip)
            )
            logging.info(f"Inserted sample: [{tip.upper()}] {nama}")

    conn.commit()
    cur.close()
    conn.close()
    logging.info("✅ Migrasi sukses! Kolom 'lemari' dan 'tipe' berhasil ditambahkan dan diverifikasi.")

if __name__ == '__main__':
    run_migration()
