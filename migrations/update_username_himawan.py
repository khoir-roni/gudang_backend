import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    try:
        from app.config import Config
        return psycopg2.connect(
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            host=Config.DB_HOST,
            port=Config.DB_PORT
        )
    except Exception:
        return psycopg2.connect(
            dbname=os.environ.get("DB_NAME", "gudang"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "123456"),
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432")
        )

def update_username():
    conn = get_connection()
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    old_user = "himawan.adi"
    new_user = "himawan.adhi"

    try:
        print(f"[*] Memeriksa pengguna '{old_user}'...")
        cur.execute("SELECT id, username FROM users WHERE username = %s;", (old_user,))
        user_row = cur.fetchone()

        if not user_row:
            cur.execute("SELECT id, username FROM users WHERE username = %s;", (new_user,))
            existing_new = cur.fetchone()
            if existing_new:
                print(f"[!] Pengguna '{new_user}' sudah ada (ID: {existing_new['id']}). Tidak ada perubahan yang diperlukan.")
                conn.rollback()
                return
            else:
                print(f"[!] Pengguna '{old_user}' tidak ditemukan di tabel users.")
                conn.rollback()
                return

        user_id = user_row["id"]
        print(f"[+] Ditemukan pengguna '{old_user}' dengan ID: {user_id}")

        # Update users
        cur.execute("UPDATE users SET username = %s WHERE id = %s;", (new_user, user_id))
        print(f"[+] Tabel 'users' diperbarui: '{old_user}' -> '{new_user}'")

        # Update history_barang
        cur.execute("UPDATE history_barang SET username = %s WHERE username = %s;", (new_user, old_user))
        hb_count = cur.rowcount
        print(f"[+] Tabel 'history_barang' diperbarui: {hb_count} baris mutasi diselaraskan ke '{new_user}'")

        # Update history_login
        cur.execute("UPDATE history_login SET username = %s WHERE username = %s;", (new_user, old_user))
        hl_count = cur.rowcount
        print(f"[+] Tabel 'history_login' diperbarui: {hl_count} baris log login diselaraskan ke '{new_user}'")

        conn.commit()
        print(f"[V] SUKSES: Username berhasil diubah menjadi '{new_user}' secara konsisten!")

    except Exception as e:
        conn.rollback()
        print(f"[X] ERROR: Terjadi kesalahan, transaksi dibatalkan: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    update_username()
