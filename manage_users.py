import sys
import getpass
import argparse
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

# Database Configuration
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
    import os
    DB_CONFIG = {
        "dbname": os.environ.get("DB_NAME", "gudang"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "123456"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432")
    }

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def list_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT u.id, u.username, 
               (SELECT COUNT(*) FROM history_login hl WHERE hl.username = u.username) AS total_login,
               (SELECT MAX(hl.waktu) FROM history_login hl WHERE hl.username = u.username) AS last_login,
               (SELECT COUNT(*) FROM history_barang hb WHERE hb.username = u.username) AS total_aksi
        FROM users u
        ORDER BY u.id ASC;
    """)
    users = cur.fetchall()
    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("                    DAFTAR PENGGUNA SISTEM GUDANG SAGULING")
    print("=" * 80)
    print(f"{'ID':<5} | {'Username':<18} | {'Login':<7} | {'Aksi Gudang':<12} | {'Login Terakhir'}")
    print("-" * 80)
    if not users:
        print(" (Belum ada pengguna terdaftar)")
    else:
        for u in users:
            last = str(u['last_login']).split('.')[0] if u['last_login'] else '-'
            print(f"{u['id']:<5} | {u['username']:<18} | {u['total_login']:<7} | {u['total_aksi']:<12} | {last}")
    print("=" * 80 + "\n")
    return users

def add_user(username=None, password=None):
    if not username:
        username = input(" Masukkan username baru: ").strip()
    if not username:
        print(" [BATAL] Username tidak boleh kosong.")
        return False

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s);", (username,))
    if cur.fetchone():
        print(f" [GAGAL] Pengguna dengan username '{username}' sudah terdaftar!")
        cur.close()
        conn.close()
        return False

    if not password:
        try:
            password = getpass.getpass(" Masukkan password: ")
        except Exception:
            password = input(" Masukkan password: ")

    if not password:
        print(" [BATAL] Password tidak boleh kosong.")
        cur.close()
        conn.close()
        return False

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id;", (username, hashed))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    print(f" [SUKSES] Pengguna '{username}' (ID: {new_id}) berhasil ditambahkan!")
    return True

def reset_password(username=None, new_password=None):
    if not username:
        username = input(" Masukkan username yang ingin direset passwordnya: ").strip()
    if not username:
        print(" [BATAL] Username tidak boleh kosong.")
        return False

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username FROM users WHERE LOWER(username) = LOWER(%s);", (username,))
    row = cur.fetchone()
    if not row:
        print(f" [GAGAL] Pengguna '{username}' tidak ditemukan!")
        cur.close()
        conn.close()
        return False

    user_id, exact_username = row

    if not new_password:
        try:
            new_password = getpass.getpass(f" Masukkan password baru untuk '{exact_username}': ")
        except Exception:
            new_password = input(f" Masukkan password baru untuk '{exact_username}': ")

    if not new_password:
        print(" [BATAL] Password baru tidak boleh kosong.")
        cur.close()
        conn.close()
        return False

    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cur.execute("UPDATE users SET password = %s WHERE id = %s;", (hashed, user_id))
    conn.commit()
    cur.close()
    conn.close()

    print(f" [SUKSES] Password untuk pengguna '{exact_username}' berhasil diubah!")
    return True

def delete_user(username=None):
    if not username:
        username = input(" Masukkan username yang ingin dihapus: ").strip()
    if not username:
        print(" [BATAL] Username tidak boleh kosong.")
        return False

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username FROM users WHERE LOWER(username) = LOWER(%s);", (username,))
    row = cur.fetchone()
    if not row:
        print(f" [GAGAL] Pengguna '{username}' tidak ditemukan!")
        cur.close()
        conn.close()
        return False

    user_id, exact_username = row
    confirm = input(f" [PERINGATAN] Yakin ingin menghapus pengguna '{exact_username}' (ID: {user_id})? (y/N): ").strip().lower()
    if confirm != 'y':
        print(" [BATAL] Penghapusan pengguna dibatalkan.")
        cur.close()
        conn.close()
        return False

    cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    print(f" [SUKSES] Pengguna '{exact_username}' berhasil dihapus.")
    return True

def view_login_history(limit=20):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, username, aksi, waktu
        FROM history_login
        ORDER BY waktu DESC
        LIMIT %s;
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print(f"           {limit} RIWAYAT LOGIN TERAKHIR SISTEM GUDANG")
    print("=" * 70)
    print(f"{'Waktu':<22} | {'Username':<18} | {'Aktivitas'}")
    print("-" * 70)
    if not rows:
        print(" (Belum ada riwayat login)")
    else:
        for r in rows:
            waktu = str(r['waktu']).split('.')[0] if r['waktu'] else '-'
            print(f"{waktu:<22} | {r['username']:<18} | {r['aksi']}")
    print("=" * 70 + "\n")

def interactive_menu():
    while True:
        print("\n" + "#" * 55)
        print("   SISTEM MANAJEMEN PENGGUNA GUDANG PLTA SAGULING")
        print("#" * 55)
        print(" [1] Lihat Semua Pengguna")
        print(" [2] Tambah Pengguna Baru (Auto Bcrypt Hash)")
        print(" [3] Reset / Ganti Password Pengguna")
        print(" [4] Hapus Pengguna")
        print(" [5] Lihat Riwayat Login Terakhir")
        print(" [0] Keluar")
        print("-" * 55)
        choice = input(" Pilih menu (0-5): ").strip()

        if choice == '1':
            list_users()
        elif choice == '2':
            add_user()
        elif choice == '3':
            reset_password()
        elif choice == '4':
            delete_user()
        elif choice == '5':
            view_login_history(20)
        elif choice == '0':
            print("\n Terima kasih. Keluar dari manajemen pengguna.\n")
            break
        else:
            print(" [PILIHAN TIDAK VALID] Silakan masukkan angka 0 sampai 5.")

def main():
    parser = argparse.ArgumentParser(description="Manajemen Pengguna Database Gudang Saguling")
    parser.add_argument("--list", action="store_true", help="Tampilkan daftar seluruh pengguna")
    parser.add_argument("--add", nargs=2, metavar=('USERNAME', 'PASSWORD'), help="Tambah pengguna baru")
    parser.add_argument("--reset-password", nargs=2, metavar=('USERNAME', 'NEW_PASSWORD'), help="Reset password pengguna")
    parser.add_argument("--delete", metavar='USERNAME', help="Hapus pengguna")
    parser.add_argument("--history", type=int, nargs='?', const=20, help="Tampilkan riwayat login")

    args = parser.parse_args()

    if args.list:
        list_users()
    elif args.add:
        add_user(args.add[0], args.add[1])
    elif args.reset_password:
        reset_password(args.reset_password[0], args.reset_password[1])
    elif args.delete:
        delete_user(args.delete)
    elif args.history is not None:
        view_login_history(args.history)
    else:
        # Default: Mode Interaktif
        interactive_menu()

if __name__ == "__main__":
    main()
