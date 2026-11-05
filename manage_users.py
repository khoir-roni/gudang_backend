import sys
import os
import getpass
import argparse
import socket
import subprocess
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

# Deteksi Host & Target
HOST_NAME = socket.gethostname()
IS_PC_SERVER = (HOST_NAME == "DESKTOP-GB64DDS")
TARGET_DESC = "PC SERVER (DESKTOP-GB64DDS)" if IS_PC_SERVER else f"LAPTOP LOKAL ({HOST_NAME})"

# Kandidat Jalur SSH ke PC Server (Urutan Prioritas Fallback)
SSH_HOST_CANDIDATES = [
    {
        "host": "100.119.4.53",
        "name": "Tailscale VPN",
        "desc": "Tailscale VPN (100.119.4.53)"
    },
    {
        "host": "gudangapp-server2",
        "name": "Cloudflare Tunnel",
        "desc": "Cloudflare Tunnel (gudangapp-server2 -> ssh.gudangapp-hki.my.id)"
    },
    {
        "host": "gudangapp-lokal",
        "name": "Jaringan LAN Lokal",
        "desc": "Jaringan LAN Lokal (gudangapp-lokal -> 192.168.31.58)"
    }
]

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
    DB_CONFIG = {
        "dbname": os.environ.get("DB_NAME", "gudang"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "123456"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432")
    }

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def detect_active_host(quiet=False):
    """
    Mendeteksi host SSH PC Server yang aktif dengan urutan:
    1. 100.119.4.53 (Tailscale VPN)
    2. gudangapp-server2 (Cloudflare Tunnel)
    3. gudangapp-lokal (Jaringan LAN Lokal)
    """
    if not quiet:
        print("\n [INFO] Memeriksa ketersediaan jalur koneksi SSH ke PC Server...")
    for candidate in SSH_HOST_CANDIDATES:
        host = candidate["host"]
        name = candidate["name"]
        if not quiet:
            print(f"  - Menguji jalur {name} ({host})... ", end="", flush=True)
        try:
            res = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", host, "echo PING_OK"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=6
            )
            if res.returncode == 0 and "PING_OK" in res.stdout:
                if not quiet:
                    print("[AKTIF]")
                return host
            else:
                if not quiet:
                    print("[OFFLINE / TIMEOUT]")
        except subprocess.TimeoutExpired:
            if not quiet:
                print("[TIMEOUT]")
        except Exception as e:
            if not quiet:
                print(f"[GAGAL: {e}]")

    if not quiet:
        print(" [PERINGATAN] Tidak ada jalur yang merespons ping cepat. Menggunakan fallback 100.119.4.53.")
    return "100.119.4.53"

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
    print(f"            Target Database: {TARGET_DESC}")
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
    print(f"            Target Database: {TARGET_DESC}")
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

def switch_to_server(target_host=None):
    if not target_host or target_host.lower() == 'auto':
        target_host = detect_active_host()
    desc = next((item["desc"] for item in SSH_HOST_CANDIDATES if item["host"] == target_host), target_host)
    print(f"\n [INFO] Menghubungkan ke PC Server via {desc}...\n", flush=True)
    sys.stdout.flush()
    tty_flag = "-t" if sys.stdin.isatty() else ""
    cmd = f'ssh {tty_flag} {target_host} "cd D:\\gudangWarehouse\\gudang_backend; .\\.venv\\Scripts\\python.exe manage_users.py"'.strip()
    os.system(cmd)

def interactive_menu():
    while True:
        print("\n" + "#" * 60)
        print("   SISTEM MANAJEMEN PENGGUNA GUDANG PLTA SAGULING")
        print(f"   Target: {TARGET_DESC}")
        print("#" * 60)
        print(" [1] Lihat Semua Pengguna")
        print(" [2] Tambah Pengguna Baru (Auto Bcrypt Hash)")
        print(" [3] Reset / Ganti Password Pengguna")
        print(" [4] Hapus Pengguna")
        print(" [5] Lihat Riwayat Login Terakhir")
        if not IS_PC_SERVER:
            print(" [S] Beralih / Buka Database PC SERVER (Auto-detect / Multi-host)")
        print(" [0] Keluar")
        print("-" * 60)
        choice = input(" Pilih menu: ").strip()

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
        elif choice.upper() == 'S' and not IS_PC_SERVER:
            switch_to_server()
        elif choice == '0':
            print("\n Terima kasih. Keluar dari manajemen pengguna.\n")
            break
        else:
            print(" [PILIHAN TIDAK VALID] Silakan masukkan opsi yang sesuai di menu.")

def main():
    parser = argparse.ArgumentParser(description="Manajemen Pengguna Database Gudang Saguling")
    parser.add_argument("--server", action="store_true", help="Arahkan langsung ke database PC Server via SSH")
    parser.add_argument("--host", default=None, help="Tentukan host SSH spesifik (100.119.4.53, gudangapp-server2, gudangapp-lokal) atau 'auto'")
    parser.add_argument("--list", action="store_true", help="Tampilkan daftar seluruh pengguna")
    parser.add_argument("--add", nargs=2, metavar=('USERNAME', 'PASSWORD'), help="Tambah pengguna baru")
    parser.add_argument("--reset-password", nargs=2, metavar=('USERNAME', 'NEW_PASSWORD'), help="Reset password pengguna")
    parser.add_argument("--delete", metavar='USERNAME', help="Hapus pengguna")
    parser.add_argument("--history", type=int, nargs='?', const=20, help="Tampilkan riwayat login")

    args = parser.parse_args()

    if args.server and not IS_PC_SERVER:
        target_host = args.host if (args.host and args.host.lower() != 'auto') else detect_active_host()
        desc = next((item["desc"] for item in SSH_HOST_CANDIDATES if item["host"] == target_host), target_host)

        # Rekonstruksi argumen tanpa --server dan tanpa --host
        forwarded_args = []
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--server":
                i += 1
                continue
            if arg == "--host":
                i += 2
                continue
            forwarded_args.append(arg)
            i += 1

        remote_cmd = f"cd D:\\gudangWarehouse\\gudang_backend; .\\.venv\\Scripts\\python.exe manage_users.py {' '.join(forwarded_args)}".strip()
        print(f"\n [INFO] Menjalankan perintah remote di PC Server via {desc}...\n", flush=True)
        sys.stdout.flush()
        tty_flag = "-t" if sys.stdin.isatty() else ""
        cmd = f'ssh {tty_flag} {target_host} "{remote_cmd}"'.strip()
        os.system(cmd)
        return

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
