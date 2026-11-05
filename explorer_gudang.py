#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitas Interaktif & CLI Penjelajah Data Gudang PLTA Saguling
Mendukung Dual-Target (Laptop Lokal & PC Server) dengan audit komparasi side-by-side.
"""

import sys
import os
import json
import socket
import subprocess
import argparse
from datetime import date, datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Konfigurasi Encoding Output Terminal
try:
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Identifikasi Host
HOST_NAME = socket.gethostname()
IS_PC_SERVER = (HOST_NAME == "DESKTOP-GB64DDS")

# Jalur SSH Kandidat ke PC Server (Urutan Prioritas Fallback)
SSH_HOST_CANDIDATES = [
    {
        "host": "100.119.4.53",
        "name": "Tailscale VPN",
        "desc": "Tailscale VPN [100.119.4.53]"
    },
    {
        "host": "gudangapp-server2",
        "name": "Cloudflare Tunnel",
        "desc": "Cloudflare Tunnel [ssh.gudangapp-hki.my.id]"
    },
    {
        "host": "gudangapp-lokal",
        "name": "Jaringan LAN Lokal",
        "desc": "Jaringan LAN Lokal [192.168.31.58]"
    }
]

# Konfigurasi Default PostgreSQL Lokal
try:
    from app.config import Config
    LOCAL_DB_CONFIG = {
        "dbname": Config.DB_NAME,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "host": Config.DB_HOST,
        "port": Config.DB_PORT
    }
except Exception:
    LOCAL_DB_CONFIG = {
        "dbname": os.environ.get("DB_NAME", "gudang"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "123456"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432")
    }


def detect_active_host(quiet=True):
    """
    Mendeteksi jalur SSH PC Server yang aktif dengan urutan:
    1. 100.119.4.53 (Tailscale VPN)
    2. gudangapp-server2 (Cloudflare Tunnel)
    3. gudangapp-lokal (Jaringan LAN Lokal)
    """
    if not quiet:
        print("\n [INFO] Mendeteksi ketersediaan jalur koneksi SSH ke PC Server...")
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
                    print("[OFFLINE]")
        except Exception:
            if not quiet:
                print("[TIMEOUT]")

    if not quiet:
        print(" [PERINGATAN] Menggunakan fallback default 100.119.4.53.")
    return "100.119.4.53"


def get_local_connection():
    """Membuka koneksi psycopg2 ke database PostgreSQL lokal."""
    return psycopg2.connect(**LOCAL_DB_CONFIG)


def get_raw_stats_dict(conn):
    """Mengambil dictionary statistik mentah untuk perbandingan cepat atau format JSON."""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Tabel barang total & stok
    cur.execute("""
        SELECT 
            count(*) AS total_jenis,
            coalesce(sum(jumlah), 0) AS total_stok,
            count(*) FILTER (WHERE tipe = 'material') AS material_jenis,
            coalesce(sum(jumlah) FILTER (WHERE tipe = 'material'), 0) AS material_stok,
            count(*) FILTER (WHERE tipe = 'tool') AS tool_jenis,
            coalesce(sum(jumlah) FILTER (WHERE tipe = 'tool'), 0) AS tool_stok
        FROM barang;
    """)
    barang_row = cur.fetchone()

    # 2. Kalibrasi tools
    cur.execute("""
        SELECT
            count(*) FILTER (WHERE tgl_kalibrasi IS NOT NULL) AS wajib_kalibrasi,
            count(*) FILTER (WHERE tgl_kalibrasi < CURRENT_DATE) AS expired,
            count(*) FILTER (WHERE tgl_kalibrasi >= CURRENT_DATE AND tgl_kalibrasi <= CURRENT_DATE + INTERVAL '30 days') AS warning_30d,
            count(*) FILTER (WHERE tgl_kalibrasi > CURRENT_DATE + INTERVAL '30 days') AS valid_aktif
        FROM barang;
    """)
    kalibrasi_row = cur.fetchone()

    # 3. Material kritis
    cur.execute("""
        SELECT
            count(*) FILTER (WHERE jumlah = 0) AS stok_habis,
            count(*) FILTER (WHERE jumlah > 0 AND jumlah <= 2) AS stok_kritis
        FROM barang
        WHERE tipe = 'material';
    """)
    kritis_row = cur.fetchone()

    # 4. Users, history_barang, history_login
    cur.execute("SELECT count(*) AS total_users FROM users;")
    users_count = cur.fetchone()['total_users']

    cur.execute("SELECT count(*) AS total_mutasi, max(waktu) AS latest_mutasi FROM history_barang;")
    mutasi_row = cur.fetchone()

    cur.execute("SELECT count(*) AS total_login, max(waktu) AS latest_login FROM history_login;")
    login_row = cur.fetchone()

    cur.close()

    return {
        "total_jenis": int(barang_row['total_jenis']),
        "total_stok": int(barang_row['total_stok']),
        "material_jenis": int(barang_row['material_jenis']),
        "material_stok": int(barang_row['material_stok']),
        "tool_jenis": int(barang_row['tool_jenis']),
        "tool_stok": int(barang_row['tool_stok']),
        "wajib_kalibrasi": int(kalibrasi_row['wajib_kalibrasi']),
        "expired": int(kalibrasi_row['expired']),
        "warning_30d": int(kalibrasi_row['warning_30d']),
        "valid_aktif": int(kalibrasi_row['valid_aktif']),
        "stok_habis": int(kritis_row['stok_habis']),
        "stok_kritis": int(kritis_row['stok_kritis']),
        "total_users": int(users_count),
        "total_mutasi": int(mutasi_row['total_mutasi']),
        "latest_mutasi": str(mutasi_row['latest_mutasi']).split('.')[0] if mutasi_row['latest_mutasi'] else "-",
        "total_login": int(login_row['total_login']),
        "latest_login": str(login_row['latest_login']).split('.')[0] if login_row['latest_login'] else "-"
    }


def show_summary(conn, target_name):
    """Menampilkan ringkasan eksekutif dan statistik gudang secara terstruktur."""
    stats = get_raw_stats_dict(conn)

    print("\n" + "=" * 82)
    print("           RINGKASAN EKSEKUTIF & STATISTIK INVENTARIS GUDANG SAGULING")
    print(f"            Target Database: {target_name}")
    print("=" * 82)

    print(" 📦 1. REKAPITULASI INVENTARIS BARANG:")
    print(f"    • Total Jenis Barang Terdaftar : {stats['total_jenis']:,} item")
    print(f"    • Total Stok Fisik Tersimpan   : {stats['total_stok']:,} unit")
    print(f"      - Material Habis Pakai       : {stats['material_jenis']:,} item ({stats['material_stok']:,} unit fisik)")
    print(f"      - Tools / Perkakas Bengkel   : {stats['tool_jenis']:,} item ({stats['tool_stok']:,} unit fisik)")
    print()

    print(" 🔧 2. STATUS KALIBRASI PERKAKAS UKUR:")
    print(f"    • Instrumen Wajib Kalibrasi    : {stats['wajib_kalibrasi']} unit")
    print(f"      - [🔴 EXPIRED / KEDALUWARSA] : {stats['expired']} alat (Wajib dikalibrasi ulang)")
    print(f"      - [🟡 JATUH TEMPO <= 30 HARI]: {stats['warning_30d']} alat (Perlu dijadwalkan)")
    print(f"      - [🟢 VALID & AKTIF]         : {stats['valid_aktif']} alat (Siap operasi)")
    print()

    print(" ⚠️ 3. PEMANTAUAN STOK KRITIS MATERIAL (<= 2 UNIT):")
    print(f"      - [🔴 HABIS TOTAL (0 Unit)]  : {stats['stok_habis']} item")
    print(f"      - [🟡 MENIPIS / KRITIS (1-2)]: {stats['stok_kritis']} item")
    if stats['stok_habis'] + stats['stok_kritis'] > 0:
        print("      * Saran: Periksa Menu [4] untuk melihat daftar item pengadaan darurat.")
    print()

    print(" 👥 4. PENGGUNA & AUDIT AKTIVITAS:")
    print(f"    • Pengguna Terdaftar (users)   : {stats['total_users']} akun")
    print(f"    • Log Transaksi Mutasi Barang  : {stats['total_mutasi']:,} mutasi")
    print(f"      - Transaksi Terakhir         : {stats['latest_mutasi']}")
    print(f"    • Log Aktivitas Login Sistem   : {stats['total_login']:,} sesi")
    print(f"      - Login Terakhir             : {stats['latest_login']}")
    print("=" * 82 + "\n")


def search_barang(conn, query, target_name):
    """Mencari barang secara case-insensitive berdasarkan nama, lemari, atau lokasi."""
    if not query or not query.strip():
        query = input(" Masukkan kata kunci pencarian (nama/lemari/lokasi): ").strip()
    if not query:
        print(" [BATAL] Kata kunci pencarian tidak boleh kosong.")
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)
    pattern = f"%{query}%"
    cur.execute("""
        SELECT id, nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi,
               (CURRENT_DATE - tgl_kalibrasi) AS days_expired,
               (tgl_kalibrasi - CURRENT_DATE) AS days_remaining
        FROM barang
        WHERE nama_barang ILIKE %s OR lemari ILIKE %s OR lokasi ILIKE %s
        ORDER BY tipe ASC, nama_barang ASC;
    """, (pattern, pattern, pattern))
    rows = cur.fetchall()
    cur.close()

    today = date.today()
    print("\n" + "=" * 96)
    print(f"             HASIL PENCARIAN BARANG: '{query}' ({len(rows)} item ditemukan)")
    print(f"              Target Database: {target_name}")
    print("=" * 96)
    print(f"{'ID':<5} | {'Nama Barang':<34} | {'Tipe':<8} | {'Stok':<5} | {'Lemari':<10} | {'Lokasi':<10} | {'Status Kalibrasi'}")
    print("-" * 96)

    if not rows:
        print(f" [INFO] Tidak ada barang yang cocok dengan kata kunci '{query}'.")
    else:
        for r in rows:
            tipe = r['tipe'] or 'tool'
            tgl = r['tgl_kalibrasi']
            if tgl is not None:
                if tgl < today:
                    status = f"[🔴 EXP: {tgl} (-{r['days_expired']}h)]"
                elif r['days_remaining'] <= 30:
                    status = f"[🟡 WARN: {tgl} ({r['days_remaining']}h)]"
                else:
                    status = f"[🟢 VAL: {tgl}]"
            else:
                status = "-"

            nama = (r['nama_barang'][:31] + '...') if len(r['nama_barang']) > 34 else r['nama_barang']
            print(f"{r['id']:<5} | {nama:<34} | {tipe:<8} | {r['jumlah']:<5} | {r['lemari']:<10} | {r['lokasi']:<10} | {status}")
    print("=" * 96 + "\n")


def list_tools_calibration(conn, target_name):
    """Menampilkan daftar perkakas ukur yang memiliki jadwal kalibrasi."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT id, nama_barang, jumlah, lemari, lokasi, tgl_kalibrasi,
               (CURRENT_DATE - tgl_kalibrasi) AS days_expired,
               (tgl_kalibrasi - CURRENT_DATE) AS days_remaining
        FROM barang
        WHERE tipe = 'tool' AND tgl_kalibrasi IS NOT NULL
        ORDER BY tgl_kalibrasi ASC;
    """)
    rows = cur.fetchall()
    cur.close()

    today = date.today()
    print("\n" + "=" * 98)
    print("                   DAFTAR PERKAKAS & STATUS KALIBRASI ALAT UKUR")
    print(f"                    Target Database: {target_name}")
    print("=" * 98)
    print(f"{'ID':<5} | {'Nama Alat Ukur':<34} | {'Stok':<5} | {'Lemari':<10} | {'Lokasi':<10} | {'Tgl Kalibrasi':<13} | {'Status'}")
    print("-" * 98)

    if not rows:
        print(" (Belum ada alat ukur yang dicatat tanggal kalibrasinya)")
    else:
        for r in rows:
            tgl = r['tgl_kalibrasi']
            if tgl < today:
                badge = f"[🔴 EXPIRED: -{r['days_expired']} hari]"
            elif r['days_remaining'] <= 30:
                badge = f"[🟡 WARNING: sisa {r['days_remaining']} hari]"
            else:
                badge = f"[🟢 VALID: sisa {r['days_remaining']} hari]"

            nama = (r['nama_barang'][:31] + '...') if len(r['nama_barang']) > 34 else r['nama_barang']
            print(f"{r['id']:<5} | {nama:<34} | {r['jumlah']:<5} | {r['lemari']:<10} | {r['lokasi']:<10} | {str(tgl):<13} | {badge}")
    print("=" * 98 + "\n")


def list_critical_materials(conn, target_name):
    """Menampilkan daftar material habis pakai dengan jumlah stok kritis (<= 2)."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT id, nama_barang, jumlah, lemari, lokasi
        FROM barang
        WHERE tipe = 'material' AND jumlah <= 2
        ORDER BY jumlah ASC, nama_barang ASC;
    """)
    rows = cur.fetchall()
    cur.close()

    print("\n" + "=" * 90)
    print("            DAFTAR MATERIAL KRITIS DENGAN STOK MENIPIS (STOK <= 2)")
    print(f"                      Target Database: {target_name}")
    print("=" * 90)
    print(f"{'ID':<5} | {'Nama Material':<38} | {'Stok':<6} | {'Lemari':<12} | {'Lokasi':<12} | {'Status'}")
    print("-" * 90)

    if not rows:
        print(" [AMAN] Tidak ada material dengan stok kritis. Seluruh material memiliki stok >= 3 unit.")
    else:
        for r in rows:
            stok = r['jumlah']
            if stok == 0:
                badge = "[🔴 HABIS TOTAL (0)]"
            elif stok == 1:
                badge = "[🟡 SANGAT KRITIS (1)]"
            else:
                badge = "[🟡 MENIPIS (2)]"

            nama = (r['nama_barang'][:35] + '...') if len(r['nama_barang']) > 38 else r['nama_barang']
            print(f"{r['id']:<5} | {nama:<38} | {stok:<6} | {r['lemari']:<12} | {r['lokasi']:<12} | {badge}")

        print("-" * 90)
        print(" ⚠️  PERINGATAN: Segera ajukan Bon Permintaan Barang (BPB) / pengadaan logistik")
        print("     untuk item bertanda [🔴 HABIS] dan [🟡 SANGAT KRITIS].")
    print("=" * 90 + "\n")


def audit_mutasi(conn, target_name, limit=20):
    """Menampilkan log riwayat mutasi transaksi keluar-masuk barang."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT 
            id,
            to_char(waktu, 'YYYY-MM-DD HH24:MI:SS') AS waktu_str,
            coalesce(username, '-') AS username,
            coalesce(aksi, '-') AS aksi,
            coalesce(nama_barang, '-') AS nama_barang,
            coalesce(jumlah, 0) AS jumlah,
            coalesce(lemari, '-') AS lemari,
            coalesce(lokasi, '-') AS lokasi,
            coalesce(tipe, 'tool') AS tipe
        FROM history_barang
        ORDER BY waktu DESC
        LIMIT %s;
    """, (limit,))
    rows = cur.fetchall()
    cur.close()

    print("\n" + "=" * 105)
    print(f"             AUDIT JEJAK MUTASI TRANSAKSI GUDANG ({limit} TRANSAKSI TERAKHIR)")
    print(f"                      Target Database: {target_name}")
    print("=" * 105)
    print(f"{'Waktu':<19} | {'Teknisi':<15} | {'Aksi':<12} | {'Nama Barang':<30} | {'Qty':<4} | {'Lemari':<8} | {'Lokasi'}")
    print("-" * 105)

    if not rows:
        print(" (Belum ada catatan riwayat mutasi barang)")
    else:
        for r in rows:
            nama = (r['nama_barang'][:27] + '...') if len(r['nama_barang']) > 30 else r['nama_barang']
            user = (r['username'][:13] + '..') if len(r['username']) > 15 else r['username']
            print(f"{r['waktu_str']:<19} | {user:<15} | {r['aksi']:<12} | {nama:<30} | {r['jumlah']:<4} | {r['lemari']:<8} | {r['lokasi']}")
    print("=" * 105 + "\n")


def audit_users_login(conn, target_name):
    """Menampilkan 9 pengguna resmi dan log aktivitas login terakhir."""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT u.id, u.username, 
               (SELECT COUNT(*) FROM history_login hl WHERE hl.username = u.username) AS total_login,
               (SELECT MAX(hl.waktu) FROM history_login hl WHERE hl.username = u.username) AS last_login,
               (SELECT COUNT(*) FROM history_barang hb WHERE hb.username = u.username) AS total_mutasi
        FROM users u
        ORDER BY u.id ASC;
    """)
    users = cur.fetchall()

    cur.execute("""
        SELECT id, username, aksi, to_char(waktu, 'YYYY-MM-DD HH24:MI:SS') AS waktu_str
        FROM history_login
        ORDER BY waktu DESC
        LIMIT 15;
    """)
    logins = cur.fetchall()
    cur.close()

    print("\n" + "=" * 80)
    print("                 DAFTAR PENGGUNA RESMI SISTEM GUDANG SAGULING")
    print(f"                      Target Database: {target_name}")
    print("=" * 80)
    print(f"{'ID':<5} | {'Username':<18} | {'Login':<7} | {'Mutasi Gudang':<14} | {'Login Terakhir'}")
    print("-" * 80)
    for u in users:
        last = str(u['last_login']).split('.')[0] if u['last_login'] else '-'
        print(f"{u['id']:<5} | {u['username']:<18} | {u['total_login']:<7} | {u['total_mutasi']:<14} | {last}")
    print("=" * 80)

    print("\n" + "=" * 70)
    print("                 15 RIWAYAT LOGIN TERAKHIR")
    print("=" * 70)
    print(f"{'Waktu':<19} | {'Username':<18} | {'Aktivitas / Aksi'}")
    print("-" * 70)
    for l in logins:
        print(f"{l['waktu_str']:<19} | {l['username']:<18} | {l['aksi']}")
    print("=" * 70 + "\n")


def compare_databases(target_host=None):
    """
    Membandingkan data tabel gudang antara Laptop Lokal dan PC Server secara side-by-side.
    """
    print("\n" + "=" * 85)
    print("           AUDIT KOMPARASI DATABASE: LAPTOP LOKAL VS PC SERVER")
    print("=" * 85)

    # 1. Ambil data lokal
    print(" [1/3] Mengambil metrik database Laptop Lokal (localhost)... ", end="", flush=True)
    try:
        local_conn = get_local_connection()
        local_stats = get_raw_stats_dict(local_conn)
        local_conn.close()
        print("[SUKSES]")
    except Exception as e:
        print(f"[GAGAL: {e}]")
        print(" Pastikan PostgreSQL di laptop sedang berjalan (port 5432).")
        return

    # 2. Ambil data PC Server via SSH
    if not target_host or target_host.lower() == 'auto':
        target_host = detect_active_host(quiet=True)

    desc = next((item["desc"] for item in SSH_HOST_CANDIDATES if item["host"] == target_host), target_host)
    print(f" [2/3] Mengambil metrik database PC Server via {desc}... ", end="", flush=True)

    try:
        remote_cmd = 'cd D:\\gudangWarehouse\\gudang_backend; .\\.venv\\Scripts\\python.exe explorer_gudang.py --raw-stats'
        res = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target_host, remote_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=12
        )
        if res.returncode != 0:
            print(f"[GAGAL]")
            print(f" Error detail: {res.stderr.strip()}")
            return

        # Parsing JSON output dari server
        server_output = res.stdout.strip()
        # Cari baris JSON valid
        json_line = None
        for line in server_output.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                json_line = line
                break

        if not json_line:
            print(f"[GAGAL PARSE JSON]")
            print(f" Output server: {server_output}")
            return

        server_stats = json.loads(json_line)
        print("[SUKSES]")
    except Exception as e:
        print(f"[GAGAL KONEKSI: {e}]")
        return

    # 3. Format Perbandingan Berdampingan
    print("\n" + "=" * 92)
    print(f"{'Metrik / Indikator Data':<32} | {'Laptop Lokal':<18} | {'PC Server':<18} | {'Status Selaras'}")
    print("-" * 92)

    metrics = [
        ("Total Jenis Barang", "total_jenis", "item"),
        ("  - Material Habis Pakai", "material_jenis", "item"),
        ("  - Tools / Perkakas", "tool_jenis", "item"),
        ("Total Stok Fisik Unit", "total_stok", "unit"),
        ("  - Stok Fisik Material", "material_stok", "unit"),
        ("  - Stok Fisik Tools", "tool_stok", "unit"),
        ("Alat Wajib Kalibrasi", "wajib_kalibrasi", "alat"),
        ("Material Kritis (<= 2)", "stok_kritis", "item"),
        ("Pengguna Terdaftar (users)", "total_users", "akun"),
        ("Riwayat Mutasi (history_barang)", "total_mutasi", "mutasi"),
        ("Riwayat Login (history_login)", "total_login", "log"),
        ("Waktu Mutasi Terakhir", "latest_mutasi", "str"),
        ("Waktu Login Terakhir", "latest_login", "str"),
    ]

    all_identical = True
    for label, key, unit in metrics:
        v_local = local_stats.get(key, 0)
        v_server = server_stats.get(key, 0)

        if unit == "str":
            s_local = str(v_local)
            s_server = str(v_server)
            if s_local == s_server:
                status = "[🟢 IDENTIK]"
            else:
                status = "[🟡 BEDA WAKTU]"
                all_identical = False
        else:
            s_local = f"{v_local:,} {unit}"
            s_server = f"{v_server:,} {unit}"
            diff = v_local - v_server
            if diff == 0:
                status = "[🟢 IDENTIK]"
            else:
                all_identical = False
                sign = f"+{diff}" if diff > 0 else f"{diff}"
                status = f"[🔴 SELISIH: {sign}]"

        print(f"{label:<32} | {s_local:<18} | {s_server:<18} | {status}")

    print("=" * 92)
    if all_identical:
        print(" ✅ KESIMPULAN: Database Laptop Lokal dan PC Server 100% SINKRON & IDENTIK.")
    else:
        print(" ⚠️  KESIMPULAN: Terdapat perbedaan data mutasi/stok antara Laptop dan PC Server.")
        print("     Gunakan skrip 'sync_db_from_server.bat' jika ingin menyelaraskan laptop dengan server.")
    print("=" * 92 + "\n")


def open_psql_console(target_type='local', target_host=None):
    """Membuka konsol psql interaktif ke target yang dipilih."""
    if target_type == 'server':
        if not target_host or target_host.lower() == 'auto':
            target_host = detect_active_host(quiet=True)
        desc = next((item["desc"] for item in SSH_HOST_CANDIDATES if item["host"] == target_host), target_host)
        print(f"\n [INFO] Meluncurkan sesi interaktif PSQL di PC Server via {desc}...\n", flush=True)
        tty_flag = "-t" if sys.stdin.isatty() else ""
        cmd = f'ssh {tty_flag} {target_host} "psql -U postgres -d gudang"'
        os.system(cmd)
    else:
        print("\n [INFO] Meluncurkan sesi interaktif PSQL di Laptop Lokal (localhost)...\n", flush=True)
        env = os.environ.copy()
        env["PGPASSWORD"] = LOCAL_DB_CONFIG.get("password", "123456")

        # Cari path psql lokal
        psql_candidates = [
            "psql",
            r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\16\bin\psql.exe"
        ]
        chosen_psql = None
        for p in psql_candidates:
            try:
                subprocess.run([p, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                chosen_psql = p
                break
            except Exception:
                continue

        if not chosen_psql:
            chosen_psql = "psql"

        cmd = [
            chosen_psql,
            "-U", LOCAL_DB_CONFIG.get("user", "postgres"),
            "-h", LOCAL_DB_CONFIG.get("host", "localhost"),
            "-p", str(LOCAL_DB_CONFIG.get("port", "5432")),
            "-d", LOCAL_DB_CONFIG.get("dbname", "gudang")
        ]
        try:
            subprocess.run(cmd, env=env)
        except Exception as e:
            print(f" [GAGAL] Tidak dapat membuka konsol psql: {e}")


def delegate_to_server(args_list, target_host=None):
    """Mendelegasikan eksekusi perintah ke PC Server via SSH."""
    if not target_host or target_host.lower() == 'auto':
        target_host = detect_active_host(quiet=False)
    desc = next((item["desc"] for item in SSH_HOST_CANDIDATES if item["host"] == target_host), target_host)

    # Konstruksi perintah tanpa flag --target dan --host
    cleaned_args = []
    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg in ["--target", "-t"]:
            i += 2
            continue
        if arg in ["--host"]:
            i += 2
            continue
        cleaned_args.append(arg)
        i += 1

    forwarded_str = " ".join(cleaned_args)
    remote_cmd = f"cd D:\\gudangWarehouse\\gudang_backend; .\\.venv\\Scripts\\python.exe explorer_gudang.py --target local {forwarded_str}".strip()

    print(f"\n [INFO] Menghubungkan ke PC Server via {desc}...\n", flush=True)
    sys.stdout.flush()
    tty_flag = "-t" if sys.stdin.isatty() else ""
    cmd = f'ssh {tty_flag} {target_host} "{remote_cmd}"'.strip()
    os.system(cmd)


def interactive_menu(initial_target='local', initial_host=None):
    """Menampilkan antarmuka teks interaktif (TUI) penjelajah data gudang."""
    current_target = initial_target
    target_host = initial_host

    while True:
        # Menentukan deskripsi target aktif
        if current_target == 'server' and not IS_PC_SERVER:
            if not target_host or target_host.lower() == 'auto':
                target_host = detect_active_host(quiet=True)
            desc_host = next((item["desc"] for item in SSH_HOST_CANDIDATES if item["host"] == target_host), target_host)
            active_desc = f"PC SERVER ({desc_host})"
        elif IS_PC_SERVER:
            active_desc = "PC SERVER (DESKTOP-GB64DDS - Host Lokal)"
        else:
            active_desc = "LAPTOP LOKAL (localhost:5432)"

        print("\n" + "=" * 78)
        print("               PENJELAJAH DATA GUDANG PLTA SAGULING (TUI)")
        print(f"               Target Aktif : {active_desc}")
        print("=" * 78)
        print(" [1] Ringkasan Eksekutif & Statistik Gudang")
        print(" [2] Pencarian Cepat Barang (Nama / Lemari / Lokasi)")
        print(" [3] Daftar Tools & Pelacakan Status Kalibrasi")
        print(" [4] Daftar Material & Peringatan Stok Kritis (<= 2 unit)")
        print(" [5] Audit 20 Log Mutasi Transaksi Barang (history_barang)")
        print(" [6] Audit Pengguna Terdaftar & Riwayat Login (users & history_login)")
        print(" [7] Audit Komparasi Database (Laptop Lokal vs PC Server)")
        if not IS_PC_SERVER:
            if current_target == 'local':
                print(" [8] Beralih Target -> Buka Data PC SERVER (Auto-detect SSH)")
            else:
                print(" [8] Beralih Target -> Buka Data LAPTOP LOKAL (localhost)")
        print(" [9] Buka Konsol PSQL Interaktif Langsung ke Target Ini")
        print(" [0] Keluar")
        print("=" * 78)

        choice = input(" Pilih menu (0-9): ").strip()

        if choice == '0':
            print("\n Terima kasih. Menutup penjelajah data gudang.\n")
            break

        # Jika target server dan berada di laptop, delegasikan menu interaktif ke server
        if current_target == 'server' and not IS_PC_SERVER and choice in ['1', '2', '3', '4', '5', '6']:
            flag_map = {
                '1': ['--summary'],
                '3': ['--tools'],
                '4': ['--materials'],
                '5': ['--mutasi', '20'],
                '6': ['--users']
            }
            if choice == '2':
                q = input(" Masukkan kata kunci pencarian: ").strip()
                if q:
                    delegate_to_server(['--search', q], target_host)
            elif choice in flag_map:
                delegate_to_server(flag_map[choice], target_host)
            input("\nTekan [Enter] untuk kembali ke menu...")
            continue

        # Eksekusi Lokal
        conn = None
        if choice in ['1', '2', '3', '4', '5', '6']:
            try:
                conn = get_local_connection()
            except Exception as e:
                print(f"\n [ERROR] Gagal terhubung ke database lokal: {e}")
                print(" Pastikan PostgreSQL lokal (port 5432) telah berjalan.")
                input("\nTekan [Enter] untuk kembali ke menu...")
                continue

        try:
            if choice == '1':
                show_summary(conn, active_desc)
            elif choice == '2':
                search_barang(conn, None, active_desc)
            elif choice == '3':
                list_tools_calibration(conn, active_desc)
            elif choice == '4':
                list_critical_materials(conn, active_desc)
            elif choice == '5':
                limit_input = input(" Jumlah transaksi yang ingin ditampilkan [Default: 20]: ").strip()
                limit = int(limit_input) if limit_input.isdigit() else 20
                audit_mutasi(conn, active_desc, limit)
            elif choice == '6':
                audit_users_login(conn, active_desc)
            elif choice == '7':
                compare_databases(target_host)
            elif choice == '8' and not IS_PC_SERVER:
                if current_target == 'local':
                    current_target = 'server'
                    print(" [INFO] Target database berhasil dialihkan ke PC SERVER.")
                else:
                    current_target = 'local'
                    print(" [INFO] Target database berhasil dialihkan ke LAPTOP LOKAL.")
            elif choice == '9':
                open_psql_console(current_target, target_host)
            else:
                print(" [PILIHAN TIDAK VALID] Silakan masukkan angka opsi 0-9.")
        finally:
            if conn:
                conn.close()

        if choice not in ['8', '9']:
            input("\nTekan [Enter] untuk kembali ke menu...")


def main():
    parser = argparse.ArgumentParser(description="Penjelajah Data Interaktif & Audit Database Gudang Saguling")
    parser.add_argument("--target", "-t", choices=["local", "server"], default=None,
                        help="Target database (local: laptop, server: PC server)")
    parser.add_argument("--host", default=None,
                        help="Tentukan host SSH spesifik (100.119.4.53, gudangapp-server2, gudangapp-lokal) atau 'auto'")
    parser.add_argument("--summary", action="store_true", help="Tampilkan ringkasan statistik gudang")
    parser.add_argument("--search", metavar="KEYWORD", help="Pencarian cepat barang berdasarkan nama/lemari/lokasi")
    parser.add_argument("--tools", action="store_true", help="Daftar perkakas & status kalibrasi")
    parser.add_argument("--materials", action="store_true", help="Daftar material stok kritis (<= 2 unit)")
    parser.add_argument("--mutasi", nargs="?", const=20, type=int, help="Audit log mutasi transaksi barang")
    parser.add_argument("--users", action="store_true", help="Audit pengguna terdaftar dan log login")
    parser.add_argument("--compare", action="store_true", help="Audit komparasi side-by-side Laptop vs PC Server")
    parser.add_argument("--psql", action="store_true", help="Buka prompt psql interaktif")
    parser.add_argument("--raw-stats", action="store_true", help="Keluarkan dictionary statistik dalam format JSON")

    args = parser.parse_args()

    # Mode JSON mentah untuk perbandingan cepat mesin / automation
    if args.raw_stats:
        try:
            conn = get_local_connection()
            stats = get_raw_stats_dict(conn)
            conn.close()
            print(json.dumps(stats))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        return

    # Evaluasi Target
    target = args.target
    if target is None:
        target = "local" if not IS_PC_SERVER else "server"

    # Jika target = server dan dijalankan di Laptop, delegasikan ke SSH kecuali opsi compare
    if target == "server" and not IS_PC_SERVER and not args.compare:
        forward_args = [arg for arg in sys.argv[1:] if arg not in ["--target", "-t", "server"]]
        delegate_to_server(forward_args, args.host)
        return

    # Komparasi Database Side-by-Side
    if args.compare:
        compare_databases(args.host)
        return

    # Buka Konsol PSQL
    if args.psql:
        open_psql_console(target, args.host)
        return

    # Eksekusi Opsi CLI Mandiri
    if args.summary or args.search or args.tools or args.materials or args.mutasi is not None or args.users:
        target_name = "PC SERVER (DESKTOP-GB64DDS)" if IS_PC_SERVER else "LAPTOP LOKAL (localhost)"
        try:
            conn = get_local_connection()
        except Exception as e:
            print(f" [ERROR] Tidak dapat membuka koneksi PostgreSQL: {e}")
            sys.exit(1)

        try:
            if args.summary:
                show_summary(conn, target_name)
            if args.search:
                search_barang(conn, args.search, target_name)
            if args.tools:
                list_tools_calibration(conn, target_name)
            if args.materials:
                list_critical_materials(conn, target_name)
            if args.mutasi is not None:
                audit_mutasi(conn, target_name, args.mutasi)
            if args.users:
                audit_users_login(conn, target_name)
        finally:
            conn.close()
        return

    # Default: Mode Interaktif
    interactive_menu(target, args.host)


if __name__ == "__main__":
    main()
