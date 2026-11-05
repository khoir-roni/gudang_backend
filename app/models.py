from .database import get_db
from psycopg2.extras import RealDictCursor
import bcrypt

class Tool:
    @staticmethod
    def get_all(tipe=None):
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        if tipe:
            cursor.execute("SELECT * FROM barang WHERE tipe = %s ORDER BY id ASC", (tipe,))
        else:
            cursor.execute("SELECT * FROM barang ORDER BY id ASC")
        tools = cursor.fetchall()
        cursor.close()
        for t in tools:
            if t.get('tgl_kalibrasi'):
                t['tgl_kalibrasi'] = t['tgl_kalibrasi'].strftime('%Y-%m-%d')
            else:
                t['tgl_kalibrasi'] = None
        return tools

    @staticmethod
    def create(nama_barang, jumlah, lemari, lokasi, username, tipe='tool', tgl_kalibrasi=None):
        tipe = (tipe or 'tool').lower()
        if tgl_kalibrasi in ('', 'null', 'None'):
            tgl_kalibrasi = None
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT jumlah FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s AND tipe = %s",
            (nama_barang, lemari, lokasi, tipe)
        )
        existing_barang = cursor.fetchone()

        if existing_barang:
            cursor.execute(
                "UPDATE barang SET jumlah = jumlah + %s, tgl_kalibrasi = COALESCE(%s, tgl_kalibrasi) WHERE nama_barang = %s AND lemari = %s AND lokasi = %s AND tipe = %s",
                (jumlah, tgl_kalibrasi, nama_barang, lemari, lokasi, tipe)
            )
        else:
            cursor.execute(
                "INSERT INTO barang (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi) VALUES (%s, %s, %s, %s, %s, %s)",
                (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi)
            )

        cursor.execute(
            "INSERT INTO history_barang (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi, aksi, username, waktu) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())",
            (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi, f"Tambah Barang ({tipe.upper()})", username)
        )

        db.commit()
        cursor.close()

    @staticmethod
    def update_stock(nama_barang, jumlah, lemari, lokasi, username):
        db = get_db()
        cursor = db.cursor()
        
        print(f'[update_stock] Ambil: {jumlah} x {nama_barang} dari {lemari}/{lokasi}')

        cursor.execute(
            "SELECT jumlah FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
            (nama_barang, lemari, lokasi)
        )
        barang = cursor.fetchone()
        
        print(f'[update_stock] Barang found: {barang}')

        if not barang:
            print(f'[update_stock] Barang tidak ditemukan!')
            return {"message": "Barang tidak ditemukan!"}, 404

        stok_tersisa = barang[0]
        if stok_tersisa < jumlah:
            print(f'[update_stock] Stok tidak mencukupi! Tersisa: {stok_tersisa}, diminta: {jumlah}')
            return {"message": "Stok tidak mencukupi!"}, 400

        jumlah_sisa = stok_tersisa - jumlah

        cursor.execute(
            "UPDATE barang SET jumlah = %s WHERE nama_barang = %s AND lemari = %s AND lokasi = %s",
            (jumlah_sisa, nama_barang, lemari, lokasi)
        )

        # Ambil tipe barang dan tgl_kalibrasi untuk pencatatan history
        cursor.execute("SELECT tipe, tgl_kalibrasi FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s", (nama_barang, lemari, lokasi))
        row = cursor.fetchone()
        tipe_val = row[0] if row and row[0] else 'tool'
        tgl_kalibrasi_val = row[1] if row else None

        cursor.execute(
            "INSERT INTO history_barang (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi, aksi, username, waktu) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())",
            (nama_barang, jumlah, lemari, lokasi, tipe_val, tgl_kalibrasi_val, "Ambil Barang", username)
        )

        db.commit()
        cursor.close()
        print(f'[update_stock] Success! Sisa stok: {jumlah_sisa}')
        return {"message": "Barang berhasil diambil!", "stok_tersisa": jumlah_sisa}

    @staticmethod
    def edit(id, nama_barang, jumlah_baru, lemari, lokasi, username, tipe='tool', tgl_kalibrasi=None):
        tipe = (tipe or 'tool').lower()
        if tgl_kalibrasi in ('', 'null', 'None'):
            tgl_kalibrasi = None
        db = get_db()
        cursor = db.cursor()

        # 1. Ambil data lama
        cursor.execute("SELECT jumlah, tipe FROM barang WHERE id = %s", (id,))
        current = cursor.fetchone()
        if not current:
            return {"message": "Barang tidak ditemukan!"}, 404
        jumlah_lama = current[0]

        # 2. Cek Konflik (Merge Scenario)
        cursor.execute(
            "SELECT id, jumlah FROM barang WHERE nama_barang = %s AND lemari = %s AND lokasi = %s AND tipe = %s AND id != %s",
            (nama_barang, lemari, lokasi, tipe, id)
        )
        conflict = cursor.fetchone()

        if conflict:
            # Merge: Gabungkan stok ke ID target, hapus ID lama
            target_id, target_jumlah = conflict
            new_target_jumlah = target_jumlah + jumlah_baru
            
            cursor.execute("UPDATE barang SET jumlah = %s, tgl_kalibrasi = COALESCE(%s, tgl_kalibrasi) WHERE id = %s", (new_target_jumlah, tgl_kalibrasi, target_id))
            cursor.execute("DELETE FROM barang WHERE id = %s", (id,))
            
            aksi_msg = f"Merge: Pindah {jumlah_baru} ke ID {target_id}"
            msg = "Barang berhasil digabungkan!"
        else:
            # Normal Edit: Update data dan catat selisih
            selisih = jumlah_baru - jumlah_lama
            if selisih > 0: aksi_msg = f"Tambah {selisih} barang"
            elif selisih < 0: aksi_msg = f"Ambil {abs(selisih)} barang"
            else: aksi_msg = "Tidak ada perubahan"

            cursor.execute("UPDATE barang SET nama_barang = %s, jumlah = %s, lemari = %s, lokasi = %s, tipe = %s, tgl_kalibrasi = %s WHERE id = %s", (nama_barang, jumlah_baru, lemari, lokasi, tipe, tgl_kalibrasi, id))
            msg = "Barang berhasil diupdate!"

        # Catat History
        cursor.execute(
            "INSERT INTO history_barang (nama_barang, jumlah, lemari, lokasi, tipe, tgl_kalibrasi, aksi, username, waktu) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())",
            (nama_barang, jumlah_baru, lemari, lokasi, tipe, tgl_kalibrasi, aksi_msg, username)
        )

        db.commit()
        cursor.close()
        return {"message": msg}

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
        for h in history:
            if h.get('tgl_kalibrasi'):
                h['tgl_kalibrasi'] = h['tgl_kalibrasi'].strftime('%Y-%m-%d')
            else:
                h['tgl_kalibrasi'] = None
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

class MLHarvestLog:
    @staticmethod
    def create(filename, image_path, ground_truth_label, predicted_label=None, predicted_confidence=None, uploaded_by=None):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO ml_harvest_log 
            (filename, image_path, ground_truth_label, predicted_label, predicted_confidence, uploaded_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (filename, image_path, ground_truth_label, predicted_label, predicted_confidence, uploaded_by)
        )
        log_id = cursor.fetchone()[0]
        db.commit()
        cursor.close()
        return log_id

    @staticmethod
    def get_stats():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT ground_truth_label, COUNT(*) 
            FROM ml_harvest_log 
            GROUP BY ground_truth_label 
            ORDER BY COUNT(*) DESC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        return [{"label": r[0], "count": r[1]} for r in rows]

class MLModelRelease:
    @staticmethod
    def get_active():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT version, model_filename, labels_filename, model_sha256, classes_count, accuracy, release_date
            FROM ml_model_release
            WHERE is_active = TRUE
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        return {
            "version": row[0],
            "model_filename": row[1],
            "labels_filename": row[2],
            "model_sha256": row[3],
            "classes_count": row[4],
            "accuracy": row[5],
            "release_date": row[6].isoformat() if row[6] else None
        }

    @staticmethod
    def create(version, model_filename, labels_filename, model_sha256, classes_count=54, accuracy=None, is_active=True):
        db = get_db()
        cursor = db.cursor()
        if is_active:
            cursor.execute("UPDATE ml_model_release SET is_active = FALSE")
        cursor.execute(
            """
            INSERT INTO ml_model_release
            (version, model_filename, labels_filename, model_sha256, classes_count, accuracy, is_active, release_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (version, model_filename, labels_filename, model_sha256, classes_count, accuracy, is_active)
        )
        rel_id = cursor.fetchone()[0]
        db.commit()
        cursor.close()
        return rel_id

