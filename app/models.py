from .database import get_db
from psycopg2.extras import RealDictCursor
import bcrypt

class Tool:
    @staticmethod
    def get_all():
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM barang ORDER BY id ASC")
        tools = cursor.fetchall()
        cursor.close()
        return tools

    @staticmethod
    def create(nama_barang, jumlah, lemari, lokasi, username):
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT jumlah FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
            (nama_barang, lemari, lokasi)
        )
        existing_barang = cursor.fetchone()

        if existing_barang:
            cursor.execute(
                "UPDATE barang SET jumlah = jumlah + %s WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
                (jumlah, nama_barang, lemari, lokasi)
            )
        else:
            cursor.execute(
                "INSERT INTO barang (nama_barang, jumlah, lemari, lokasi) VALUES (%s, %s, %s, %s)",
                (nama_barang, jumlah, lemari, lokasi)
            )

        cursor.execute(
            "INSERT INTO history_barang (nama_barang, jumlah, lemari, lokasi, aksi, username, waktu) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
            (nama_barang, jumlah, lemari, lokasi, "Tambah Barang", username)
        )

        db.commit()
        cursor.close()

    @staticmethod
    def update_stock(nama_barang, jumlah_diambil, lemari, lokasi, username):
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT jumlah FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
            (nama_barang, lemari, lokasi)
        )
        barang = cursor.fetchone()

        if not barang:
            return {"message": "Barang tidak ditemukan!"}, 404

        stok_tersisa = barang[0]
        if stok_tersisa < jumlah_diambil:
            return {"message": "Stok tidak mencukupi!"}, 400

        jumlah_sisa = stok_tersisa - jumlah_diambil

        cursor.execute(
            "UPDATE barang SET jumlah = %s WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
            (jumlah_sisa, nama_barang, lemari, lokasi)
        )

        cursor.execute(
            "INSERT INTO history_barang (nama_barang, jumlah, lemari, lokasi, aksi, username, waktu) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
            (nama_barang, jumlah_diambil, lemari, lokasi, "Ambil Barang", username)
        )

        db.commit()
        cursor.close()
        return {"message": "Barang berhasil diambil!", "stok_tersisa": jumlah_sisa}

    @staticmethod
    def delete(nama_barang, lemari, lokasi):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
            (nama_barang, lemari, lokasi)
        )
        db.commit()
        cursor.close()

class History:
    @staticmethod
    def get_all():
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM history_barang ORDER BY waktu DESC")
        history = cursor.fetchall()
        cursor.close()
        return history

    @staticmethod
    def delete(history_id):
        db = get_db()
        cursor = db.cursor()
        if history_id:
            cursor.execute("DELETE FROM history_barang WHERE id = %s", (history_id,))
        else:
            cursor.execute("DELETE FROM history_barang")
        db.commit()
        cursor.close()

class User:
    @staticmethod
    def create(username, password):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed_password.decode('utf-8'))
        )
        db.commit()
        cursor.close()

    @staticmethod
    def find_by_username(username):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        return user
