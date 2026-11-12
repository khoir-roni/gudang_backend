# ATURAN REKAYASA GUDANG_BACKEND (FLASK & POSTGRESQL)

## 1. Konsistensi Kamus Data & Audit Trail
- DDL dan model ORM (`app/models.py`) adalah ground truth utama. Dilarang membuat nama tabel/kolom fiktif.
- Tabel `history_barang` wajib mencatat kolom riil: `nama_barang`, `jumlah`, `lemari`, `lokasi`, `username`, `aksi`, dan `waktu`.
- Aksi mutasi stok wajib dicatat secara presisi (`Ambil Barang`, `Tambah Barang`, `Edit Barang`).

## 2. Sanitasi Payload & Defensive Fallback
- Endpoint mutasi stok (`/update_barang`, `/edit_barang`, `/add_barang`) wajib mengekstrak identitas pengguna dengan fallback aman:
  `username = data.get('username') or 'admin'`
- Dilarang membiarkan field username bernilai `None` atau string kosong saat menulis riwayat audit.

## 3. Pengelolaan Endpoint In-App OTA
- Konfigurasi rilis pada `app_release/version.json` wajib selalu mencerminkan rilis APK terbaru:
  `latest_version`, `version_code`, `apk_filename`, `apk_size_mb`, dan `changelog` riil.
- Endpoint `/api/app/version` dan `/api/app/download/<filename>` wajib teruji sebelum rilis diumumkan ke pengguna.

## 4. Sinkronisasi Git Dua Remote
- Setiap commit backend wajib disinkronkan ke remote `origin` (GitHub) dan `server2` (`100.119.4.53:D:/gudangWarehouse/gudang_backend`).
