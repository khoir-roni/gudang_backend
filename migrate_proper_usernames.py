#!/usr/bin/env python3
"""
migrate_proper_usernames.py
--------------------------------------------------------------------------------
Skrip migrasi nama pengguna (username) dan password di basis data `gudang`
(mendukung eksekusi di PC Server dan Laptop Lokal) berdasarkan pemetaan
di `username&pass.csv` agar format username lebih profesional/proper.

PERINGATAN KESELAMATAN:
- HANYA memodifikasi database `gudang`.
- Membuat backup tabel (users, history_login, history_barang) sebelum eksekusi.
- Berjalan dalam transaksi atomic (COMMIT jika sukses, ROLLBACK jika gagal).
--------------------------------------------------------------------------------
"""

import sys
import os
import socket
import datetime
import argparse
import subprocess
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

# Deteksi Host & Target
HOST_NAME = socket.gethostname()
IS_PC_SERVER = (HOST_NAME == "DESKTOP-GB64DDS")
TARGET_DESC = "PC SERVER (100.119.4.53 / DESKTOP-GB64DDS)" if IS_PC_SERVER else f"LAPTOP LOKAL ({HOST_NAME})"

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

# Pemetaan Akun Lama -> Baru & Password Baru
MAPPING_USERS = [
    {"old_username": "gudanguser",     "new_username": "gudang.admin", "password": "admin123"},
    {"old_username": "lukman",         "new_username": "lukman.hakim", "password": "lukman123"},
    {"old_username": "bani",           "new_username": "bani.dp",      "password": "bani123"},
    {"old_username": "himawan",        "new_username": "himawan.adi",   "password": "himawan123"},
    {"old_username": "teguhprasetyo1", "new_username": "teguh.p",      "password": "teguh123"},
    {"old_username": "hardin",         "new_username": "hardin.agung",  "password": "hardin123"},
    {"old_username": "firman",         "new_username": "firmansyah",    "password": "firman123"},
    {"old_username": "nandang",        "new_username": "nandang.w",     "password": "nandang123"},
    {"old_username": "roni",           "new_username": "ali.khoironi",  "password": "roni123"},
]

def get_connection():
    # Validasi keamanan: pastikan hanya database gudang
    if DB_CONFIG["dbname"] != "gudang":
        raise ValueError(f"CRITICAL: Target database bukan 'gudang' ({DB_CONFIG['dbname']}). Operasi dibatalkan demi keamanan!")
    return psycopg2.connect(**DB_CONFIG)

def check_table_exists(cur, table_name):
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
        ) AS tbl_exists;
    """, (table_name,))
    res = cur.fetchone()
    if isinstance(res, dict):
        return res["tbl_exists"]
    return res[0]

def create_backups(conn):
    """Membuat tabel backup lokal dengan timestamp di database gudang dan dump file."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_tables = {
        "users": f"users_backup_{ts}",
        "history_login": f"history_login_backup_{ts}",
        "history_barang": f"history_barang_backup_{ts}",
    }
    
    cur = conn.cursor()
    print(f"\n[BACKUP] Memulai pencadangan tabel database 'gudang' ({ts})...")
    
    for src_table, bkp_table in backup_tables.items():
        if check_table_exists(cur, src_table):
            cur.execute(f'CREATE TABLE "{bkp_table}" AS TABLE "{src_table}";')
            cur.execute(f'SELECT COUNT(*) FROM "{bkp_table}";')
            cnt = cur.fetchone()
            row_count = cnt["count"] if isinstance(cnt, dict) else cnt[0]
            print(f" -> Berhasil backup tabel '{src_table}' -> '{bkp_table}' ({row_count} baris)")
        else:
            print(f" -> Tabel '{src_table}' tidak ditemukan, melewati backup tabel ini.")

    cur.close()
    conn.commit()

    # Eksekusi pg_dump jika memungkinkan
    backup_file = f"backup_gudang_users_{ts}.sql"
    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = str(DB_CONFIG["password"])
        cmd = [
            "pg_dump",
            "-h", str(DB_CONFIG["host"]),
            "-p", str(DB_CONFIG["port"]),
            "-U", str(DB_CONFIG["user"]),
            "-d", str(DB_CONFIG["dbname"]),
            "-t", "users",
            "-t", "history_login",
            "-t", "history_barang",
            "-f", backup_file
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode == 0:
            print(f" -> Berhasil membuat file SQL dump: {backup_file}")
        else:
            print(f" -> Info pg_dump stderr: {res.stderr.strip()[:100]}")
    except Exception as e:
        print(f" -> Info: pg_dump file export dilewati ({e})")

    return backup_tables

def run_migration(dry_run=False):
    print("=" * 80)
    print("         MIGRASI NAMA PENGGUNA (PROPER USERNAMES) & PASSWORD")
    print(f"            Target: {TARGET_DESC}")
    if dry_run:
        print("            MODE: DRY-RUN (Tidak ada perubahan yang disimpan)")
    print("=" * 80)

    conn = get_connection()

    if not dry_run:
        create_backups(conn)

    cur = conn.cursor(cursor_factory=RealDictCursor)
    has_action_logs = check_table_exists(cur, "action_logs")

    try:
        print("\n[MIGRASI] Memproses 9 akun pengguna...")
        migration_results = []

        for item in MAPPING_USERS:
            old_u = item["old_username"]
            new_u = item["new_username"]
            pwd = item["password"]

            # Generate bcrypt hash
            hashed_pwd = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # 1. Cek keberadaan user lama dan baru di tabel users
            cur.execute("SELECT id, username FROM users WHERE LOWER(username) = LOWER(%s);", (old_u,))
            existing_old = cur.fetchone()

            cur.execute("SELECT id, username FROM users WHERE LOWER(username) = LOWER(%s);", (new_u,))
            existing_new = cur.fetchone()

            status_user = ""
            user_id = None

            if existing_old:
                user_id = existing_old["id"]
                cur.execute("""
                    UPDATE users 
                    SET username = %s, password = %s 
                    WHERE id = %s;
                """, (new_u, hashed_pwd, user_id))
                status_user = f"UPDATED (id={user_id}, '{old_u}' -> '{new_u}')"
            elif existing_new:
                user_id = existing_new["id"]
                cur.execute("""
                    UPDATE users 
                    SET password = %s 
                    WHERE id = %s;
                """, (hashed_pwd, user_id))
                status_user = f"PASSWORD_RESET (id={user_id}, '{new_u}')"
            else:
                cur.execute("""
                    INSERT INTO users (username, password) 
                    VALUES (%s, %s) 
                    RETURNING id;
                """, (new_u, hashed_pwd))
                user_id = cur.fetchone()["id"]
                status_user = f"INSERTED (id={user_id}, '{new_u}')"

            # 2. Update history_login
            cur.execute("""
                UPDATE history_login 
                SET username = %s 
                WHERE LOWER(username) = LOWER(%s);
            """, (new_u, old_u))
            login_updated = cur.rowcount

            # 3. Update history_barang
            cur.execute("""
                UPDATE history_barang 
                SET username = %s 
                WHERE LOWER(username) = LOWER(%s);
            """, (new_u, old_u))
            barang_updated = cur.rowcount

            # 4. Update action_logs jika ada
            action_updated = 0
            if has_action_logs:
                cur.execute("""
                    UPDATE action_logs 
                    SET "user" = %s 
                    WHERE LOWER("user") = LOWER(%s);
                """, (new_u, old_u))
                action_updated = cur.rowcount

            migration_results.append({
                "id": user_id,
                "old": old_u,
                "new": new_u,
                "status": status_user,
                "login_updated": login_updated,
                "barang_updated": barang_updated,
                "action_updated": action_updated
            })

        if dry_run:
            conn.rollback()
            print("\n[DRY-RUN SELESAI] Semua transaksi dibatalkan (ROLLBACK).")
        else:
            conn.commit()
            print("\n[TRANSAKSI SUKSES] Perubahan berhasil di-COMMIT ke basis data!")

        # Tampilkan ringkasan
        print("\n" + "=" * 90)
        print(f"{'ID':<4} | {'Username Baru':<16} | {'Akun Asal':<16} | {'Hist Login':<10} | {'Hist Barang':<11} | {'Status'}")
        print("-" * 90)
        for r in migration_results:
            print(f"{r['id']:<4} | {r['new']:<16} | {r['old']:<16} | {r['login_updated']:<10} | {r['barang_updated']:<11} | {r['status']}")
        print("=" * 90)

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR CRITICAL] Migrasi gagal: {e}")
        print("[ROLLBACK] Semua perubahan telah dibatalkan.")
        raise
    finally:
        cur.close()
        conn.close()

def verify_migration():
    print("\n" + "=" * 80)
    print("         VERIFIKASI OTENTIKASI & KONEKSI HISTORI PENGGUNA")
    print(f"            Target: {TARGET_DESC}")
    print("=" * 80)
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    all_ok = True
    print(f"{'Username':<16} | {'Status Password':<18} | {'Hist Login':<12} | {'Hist Barang'}")
    print("-" * 80)

    for item in MAPPING_USERS:
        u = item["new_username"]
        pwd = item["password"]
        cur.execute("SELECT id, username, password FROM users WHERE username = %s;", (u,))
        row = cur.fetchone()
        if not row:
            print(f"{u:<16} | NOT FOUND IN USERS | -            | -")
            all_ok = False
            continue

        valid = bcrypt.checkpw(pwd.encode('utf-8'), row["password"].encode('utf-8'))
        cur.execute("SELECT COUNT(*) AS total FROM history_login WHERE username = %s;", (u,))
        tot_login = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM history_barang WHERE username = %s;", (u,))
        tot_barang = cur.fetchone()["total"]

        status_str = "VALID (Bcrypt OK)" if valid else "INVALID HASH"
        if not valid:
            all_ok = False
        print(f"{u:<16} | {status_str:<18} | {tot_login:<12} | {tot_barang}")

    print("=" * 80)
    cur.close()
    conn.close()
    if all_ok:
        print(" [STATUS] SEMUA 9 AKUN BERHASIL TERVERIFIKASI OTENTIK DAN TERHUBUNG.\n")
    else:
        print(" [WARNING] TERDAPAT AKUN YANG TIDAK VALID ATAU GAGAL VERIFIKASI.\n")
    return all_ok

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrasi username & password sistem gudang.")
    parser.add_argument("--dry-run", action="store_true", help="Jalankan simulasi tanpa commit ke database.")
    parser.add_argument("--verify", action="store_true", help="Verifikasi otentikasi password dan histori pengguna.")
    args = parser.parse_args()

    if args.verify:
        verify_migration()
    else:
        run_migration(dry_run=args.dry_run)
        verify_migration()
