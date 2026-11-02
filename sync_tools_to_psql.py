import os
import sys
import pandas as pd
import psycopg2
from pathlib import Path

# Path konfigurasi & file
BASE_DIR = Path(__file__).resolve().parent
XLSX_PATH = BASE_DIR / "tabel_inventaris_tools.xlsx"
CSV_PATH = BASE_DIR / "tabel_inventaris_tools.csv"

# Import konfigurasi database jika ada
try:
    from app.config import Config
    DB_CONFIG = {
        "dbname": Config.DB_NAME,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "host": Config.DB_HOST,
        "port": Config.DB_PORT
    }
except Exception:
    DB_CONFIG = {
        "dbname": os.environ.get("DB_NAME", "gudang"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "123456"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432")
    }

def sync_tools():
    # Tentukan file sumber data (XLSX diprioritaskan, fallback ke CSV)
    if XLSX_PATH.exists():
        source_file = XLSX_PATH
        try:
            # Baris header ada di baris ke-4 (0-indexed: skiprows=3) jika menggunakan template styled
            df = pd.read_excel(source_file, skiprows=3)
            df.columns = [str(c).replace('*', '').strip() for c in df.columns]
            if "Nama Barang" not in df.columns:
                # Coba baca dari baris 0 jika pengguna menghapus header banner
                df = pd.read_excel(source_file)
                df.columns = [str(c).replace('*', '').strip() for c in df.columns]
        except Exception as e:
            print(f"Gagal membaca XLSX ({e}), beralih ke CSV...")
            df = pd.read_csv(CSV_PATH)
    elif CSV_PATH.exists():
        source_file = CSV_PATH
        df = pd.read_csv(source_file)
    else:
        print(f"ERROR: Tidak ditemukan file {XLSX_PATH.name} atau {CSV_PATH.name}")
        sys.exit(1)

    print("=" * 65)
    print(f" SINKRONISASI INVENTARIS TOOLS KE POSTGRESQL (DB: {DB_CONFIG['dbname']})")
    print(f" Sumber Berkas: {source_file.name}")
    print("=" * 65)

    # Identifikasi kolom nama, jumlah, lemari, lokasi, tipe, kalibrasi
    col_nama = next((c for c in df.columns if "nama" in c.lower()), None)
    col_jumlah = next((c for c in df.columns if "jumlah" in c.lower()), None)
    col_lemari = next((c for c in df.columns if "lemari" in c.lower()), None)
    col_lokasi = next((c for c in df.columns if "lokasi" in c.lower()), None)
    col_tipe = next((c for c in df.columns if "tipe" in c.lower()), None)
    col_kalibrasi = next((c for c in df.columns if "kalibrasi" in c.lower()), None)

    if not col_nama or not col_jumlah or not col_lemari or not col_lokasi:
        print("ERROR: Struktur kolom tidak sesuai. Pastikan ada kolom Nama Barang, Jumlah, Lemari, dan Lokasi.")
        sys.exit(1)

    # Filter baris yang memiliki nama barang valid
    df = df.dropna(subset=[col_nama])
    df = df[df[col_nama].astype(str).str.strip() != ""]

    print(f"Memproses {len(df)} baris data tools...\n")

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        inserted_count = 0
        updated_count = 0

        check_query = """
            SELECT id FROM barang 
            WHERE nama_barang = %s AND lemari = %s AND lokasi = %s;
        """

        update_query = """
            UPDATE barang 
            SET jumlah = %s, tipe = %s, tgl_kalibrasi = %s 
            WHERE id = %s;
        """

        insert_query = """
            INSERT INTO barang (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """

        history_query = """
            INSERT INTO history_barang (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi, aksi, username)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """

        for _, row in df.iterrows():
            nama_barang = str(row[col_nama]).strip()
            
            try:
                jumlah = int(row[col_jumlah])
            except (ValueError, TypeError):
                jumlah = 0

            lemari = str(row[col_lemari]).strip() if pd.notna(row[col_lemari]) else "Lemari Tools"
            lokasi = str(row[col_lokasi]).strip() if pd.notna(row[col_lokasi]) else "Bengkel K&I"
            tipe = str(row[col_tipe]).strip().lower() if col_tipe and pd.notna(row[col_tipe]) else "tool"

            tgl_kalibrasi = None
            if col_kalibrasi and pd.notna(row[col_kalibrasi]):
                val_str = str(row[col_kalibrasi]).strip()
                if val_str and val_str.lower() not in ('nan', 'none', 'null', ''):
                    tgl_kalibrasi = val_str.split(' ')[0]

            # Check if record already exists
            cur.execute(check_query, (nama_barang, lemari, lokasi))
            existing = cur.fetchone()

            if existing:
                item_id = existing[0]
                cur.execute(update_query, (jumlah, tipe, tgl_kalibrasi, item_id))
                updated_count += 1
                aksi = "UPDATE_EXCEL"
            else:
                cur.execute(insert_query, (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi))
                item_id = cur.fetchone()[0]
                inserted_count += 1
                aksi = "TAMBAH_EXCEL"

            # Catat ke history_barang
            cur.execute(history_query, (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi, aksi, "admin_import"))

        conn.commit()

        # Hitung total barang di database
        cur.execute("SELECT COUNT(*) FROM barang;")
        total_in_db = cur.fetchone()[0]

        cur.close()
        conn.close()

        print("-" * 65)
        print(" HASIL SINKRONISASI:")
        print(f"  * Barang Baru Ditambahkan  : {inserted_count}")
        print(f"  * Barang Berhasil Diupdate : {updated_count}")
        print(f"  * Total Barang di Database : {total_in_db}")
        print("-" * 65)
        print("[SUKSES] Seluruh data tools & tanggal kalibrasi berhasil disinkronkan ke PostgreSQL!")

    except psycopg2.Error as e:
        print(f"[ERROR DATABASE] {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    sync_tools()
