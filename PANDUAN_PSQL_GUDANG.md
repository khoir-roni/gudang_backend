# BUKU PANDUAN PERINTAH PSQL DATABASE GUDANG PLTA SAGULING

Panduan teknis dan referensi cepat (*cheatsheet*) konsol PostgreSQL (`psql`) untuk pemeliharaan, inspeksi, audit transaksi, dan administrasi database **`gudang`** PLTA Saguling.

---

## Daftar Isi
1. [Bab 1: Persiapan Terminal Windows & Solusi Warning Code Page](#bab-1-persiapan-terminal-windows--solusi-warning-code-page)
2. [Bab 2: Meta-Commands Navigasi Wajib PSQL](#bab-2-meta-commands-navigasi-wajib-psql)
3. [Bab 3: Query Operasional Tabel `barang` (Material & Tools)](#bab-3-query-operasional-tabel-barang-material--tools)
4. [Bab 4: Query Manajemen Pengguna (`users`) & Riwayat Login (`history_login`)](#bab-4-query-manajemen-pengguna-users--riwayat-login-history_login)
5. [Bab 5: Query Audit Jejak Transaksi Mutasi (`history_barang`)](#bab-5-query-audit-jejak-transaksi-mutasi-history_barang)
6. [Bab 6: Pemeliharaan Database & Penanganan Gangguan](#bab-6-pemeliharaan-database--penanganan-gangguan)
7. [Bab 7: Aturan Keselamatan DBA (*Poka-Yoke Safeguards*)](#bab-7-aturan-keselamatan-dba-poka-yoke-safeguards)

---

## Bab 1: Persiapan Terminal Windows & Solusi Warning Code Page

### 1.1 Mengatasi Warning Code Page di Windows
Saat menjalankan `psql` pada Command Prompt atau PowerShell di Windows, sering muncul peringatan:
```text
WARNING: Console code page (437) differs from Windows code page (1252)
         8-bit characters might not work correctly. See psql reference
         page "Notes for Windows users" for details.
```

**Penyebab:**
Terminal Windows bawaan menggunakan code page OEM (437 - English US), sedangkan sistem Windows Indonesia/Internasional memakai Windows ANSI (1252), sementara PostgreSQL menggunakan encoding UTF-8 (`UNICODE`). Perbedaan ini menyebabkan batas garis tabel ASCII berantakan atau karakter beraksen tidak terbaca.

**Solusi Pasti:**
Ubah code page terminal aktif menjadi **UTF-8 (Code Page 65001)** sebelum menjalankan `psql`:
```powershell
chcp 65001
```

> **Tips Permanen:** Tambahkan baris `chcp 65001 >$null` di berkas PowerShell Profile Anda (`$PROFILE`) agar terminal selalu siap UTF-8 saat dibuka.

---

### 1.2 Cara Masuk ke PSQL Database

#### A. Koneksi ke Database Lokal (Laptop)
Jalankan di PowerShell / CMD laptop:
```powershell
chcp 65001
psql -U postgres -h localhost -d gudang
```
*Atau jika ingin tanpa prompt password (gunakan variabel lingkungan sesi):*
```powershell
$env:PGPASSWORD="123456"; psql -U postgres -h localhost -d gudang
```

#### B. Koneksi Interaktif ke Database PC Server dari Laptop
Untuk terhubung langsung ke sesi psql di PC Server (`100.119.4.53`) dengan terminal TTY penuh:
```powershell
# Jalur 1: Via Tailscale VPN (Direkomendasikan)
ssh -t 100.119.4.53 "psql -U postgres -d gudang"

# Jalur 2: Via Cloudflare Tunnel (Jika di luar jangkauan Tailscale)
ssh -t gudangapp-server2 "psql -U postgres -d gudang"

# Jalur 3: Via LAN Lokal Gedung PLTA Saguling
ssh -t 192.168.31.58 "psql -U postgres -d gudang"
```

Ketika berhasil terhubung, terminal akan menampilkan prompt aktif:
```text
psql (16.x / 17.x)
Type "help" for help.

gudang=#
```

---

## Bab 2: Meta-Commands Navigasi Wajib PSQL

Perintah bawaan (*meta-command*) `psql` diawali dengan tanda garis miring terbalik (`\`) dan **tidak memerlukan tanda titik koma (`;`) di akhir**.

| Meta-Command | Fungsi & Kegunaan | Contoh Output / Catatan |
| :--- | :--- | :--- |
| `\l` | Menampilkan seluruh daftar database di PostgreSQL | Memeriksa apakah database `gudang` aktif |
| `\c gudang` | Berpindah koneksi (*connect*) ke database `gudang` | `You are now connected to database "gudang"` |
| `\dt` | Menampilkan daftar seluruh tabel skema publik | Melihat tabel `barang`, `users`, dll |
| `\dt+` | Menampilkan daftar tabel beserta ukuran fisik disk | Melihat ukuran data per tabel |
| `\d barang` | Memeriksa struktur kolom, tipe data, dan default | Melihat detail kolom tabel `barang` |
| `\d+ barang` | Memeriksa struktur kolom lengkap beserta indeks & komentar | Detail relasi dan constraint |
| `\x` | Beralih mode tampilan vertikal (**Expanded display**) | Sangat penting untuk membaca tabel banyak kolom |
| `\timing` | Mengaktifkan/mematikan stopwatch durasi query | `Timing is on.` (menghitung milidetik query) |
| `\conninfo` | Menampilkan informasi koneksi aktif | Mengetahui user, host, port, dan socket koneksi |
| `\s` | Melihat riwayat query yang pernah diketik | Memeriksa perintah sebelumnya |
| `\s riwayat.sql` | Menyimpan riwayat query ke dalam berkas teks | Berguna untuk dokumentasi investigasi |
| `\i berkas.sql` | Menjalankan skrip SQL dari berkas eksternal | Eksekusi otomatis migrasi atau batch update |
| `\h SELECT` | Bantuan sintaks perintah SQL standar | Panduan sintaks SQL |
| `\?` | Bantuan seluruh daftar meta-command psql | Cheatsheet lengkap bawaan psql |
| `\q` | Keluar dari konsol psql | Kembali ke PowerShell / CMD |

### Tips Emas Mode Vertikal (`\x`):
Saat query mengembalikan banyak kolom horizontal yang membuat baris tabel terpotong di terminal, ketik:
```text
gudang=# \x auto
Expanded display is used automatically.
```
Dengan mode ini, psql otomatis mengubah tampilan menjadi vertikal jika lebar layar tidak mencukupi.

---

## Bab 3: Query Operasional Tabel `barang` (Material & Tools)

Skema tabel `barang`: `id`, `nama_barang`, `jumlah`, `lokasi`, `lemari`, `tipe`, `tgl_kalibrasi`.

### 3.1 Cek Total Barang & Ringkasan Kategori
```sql
-- Cek total jenis barang terdaftar
SELECT count(*) AS total_jenis_barang FROM barang;

-- Rekapitulasi per kategori (Material vs Tools Pemeliharaan)
SELECT 
    tipe,
    count(*) AS jumlah_item,
    sum(jumlah) AS total_stok_fisik
FROM barang 
GROUP BY tipe;
```

### 3.2 Pemantauan Perkakas Berkalibrasi
```sql
-- 1. Daftar perkakas yang sudah KEDALUWARSA (Expired) kalibrasinya
SELECT 
    id, nama_barang, lokasi, lemari, tgl_kalibrasi,
    (CURRENT_DATE - tgl_kalibrasi) AS hari_terlewat
FROM barang 
WHERE tgl_kalibrasi < CURRENT_DATE 
ORDER BY tgl_kalibrasi ASC;

-- 2. Daftar perkakas yang MASIH AKTIF kalibrasinya
SELECT 
    id, nama_barang, lokasi, lemari, tgl_kalibrasi,
    (tgl_kalibrasi - CURRENT_DATE) AS sisa_hari
FROM barang 
WHERE tgl_kalibrasi >= CURRENT_DATE 
ORDER BY tgl_kalibrasi ASC;

-- 3. Peringatan dini: Perkakas yang jatuh tempo dalam 30 hari ke depan
SELECT 
    id, nama_barang, lokasi, lemari, tgl_kalibrasi
FROM barang 
WHERE tgl_kalibrasi BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '30 days')
ORDER BY tgl_kalibrasi ASC;
```

### 3.3 Pencarian Cerdas Barang (*Case-Insensitive*)
Gunakan operator `ILIKE` agar pencarian tidak sensitif huruf besar/kecil:
```sql
-- Cari alat ukur Fluke
SELECT id, nama_barang, jumlah, lokasi, lemari, tipe 
FROM barang 
WHERE nama_barang ILIKE '%fluke%';

-- Cari material kelistrikan (kabel / MCB / relay)
SELECT id, nama_barang, jumlah, lokasi, lemari 
FROM barang 
WHERE nama_barang ILIKE '%kabel%' OR nama_barang ILIKE '%mcb%';
```

### 3.4 Pantau Stok Menipis & Kritis
```sql
-- Daftar barang dengan stok menipis (jumlah <= 2)
SELECT id, nama_barang, jumlah, lokasi, lemari, tipe 
FROM barang 
WHERE jumlah <= 2 
ORDER BY jumlah ASC, nama_barang ASC;

-- Daftar barang yang habis total (stok = 0)
SELECT id, nama_barang, lokasi, lemari, tipe 
FROM barang 
WHERE jumlah = 0 
ORDER BY nama_barang ASC;
```

### 3.5 Operasi Tambah / Kurang Stok Aman (Gunakan Transaksi)
Jangan melakukan update stok secara langsung tanpa transaksi. Selalu bungkus dalam blok `BEGIN ... COMMIT`:
```sql
-- Contoh: Penambahan stok fisik 5 unit untuk barang ID 12
BEGIN;

UPDATE barang 
SET jumlah = jumlah + 5 
WHERE id = 12;

-- Verifikasi hasil sebelum disimpan permanen:
SELECT id, nama_barang, jumlah FROM barang WHERE id = 12;

-- Jika sudah benar, simpan:
COMMIT;

-- Jika ada kesalahan, batalkan dengan:
-- ROLLBACK;
```

---

## Bab 4: Query Manajemen Pengguna (`users`) & Riwayat Login (`history_login`)

Skema tabel:
- `users`: `id`, `username`, `password` (bcrypt hash)
- `history_login`: `id`, `username`, `aksi`, `waktu`

### 4.1 Melihat Pengguna Terdaftar
```sql
-- Daftar seluruh akun pengguna resmi terdaftar
SELECT id, username FROM users ORDER BY id ASC;
```

### 4.2 Analisis Aktivitas Login Pengguna
```sql
-- Rekapitulasi frekuensi login per pengguna
SELECT 
    username, 
    count(*) AS total_login,
    min(waktu) AS login_pertama,
    max(waktu) AS login_terakhir
FROM history_login 
GROUP BY username 
ORDER BY total_login DESC;

-- Melihat 15 aktivitas login terakhir
SELECT 
    id, 
    username, 
    aksi, 
    to_char(waktu, 'YYYY-MM-DD HH24:MI:SS') AS waktu_login
FROM history_login 
ORDER BY waktu DESC 
LIMIT 15;
```

---

## Bab 5: Query Audit Jejak Transaksi Mutasi (`history_barang`)

Skema tabel `history_barang`: `id`, `nama_barang`, `jumlah`, `lokasi`, `lemari`, `aksi`, `username`, `waktu`, `tipe`, `tgl_kalibrasi`.

### 5.1 Melihat 15 Mutasi Barang Terakhir
```sql
SELECT 
    to_char(waktu, 'YYYY-MM-DD HH24:MI:SS') AS waktu_transaksi,
    username,
    aksi,
    nama_barang,
    jumlah,
    lokasi,
    lemari,
    tipe
FROM history_barang 
ORDER BY waktu DESC 
LIMIT 15;
```

### 5.2 Rekapitulasi Aktivitas Transaksi per Operator / Teknisi
```sql
SELECT 
    username,
    count(*) AS total_transaksi,
    count(*) FILTER (WHERE aksi ILIKE '%tambah%') AS total_tambah,
    count(*) FILTER (WHERE aksi ILIKE '%ambil%') AS total_ambil,
    count(*) FILTER (WHERE aksi ILIKE '%edit%') AS total_edit
FROM history_barang 
GROUP BY username 
ORDER BY total_transaksi DESC;
```

### 5.3 Lacak Jejak Riwayat Khusus Satu Barang
```sql
-- Melihat seluruh riwayat transaksi untuk barang tertentu
SELECT 
    waktu, username, aksi, jumlah, lokasi, lemari 
FROM history_barang 
WHERE nama_barang ILIKE '%Tang Kombinasi%'
ORDER BY waktu DESC;
```

---

## Bab 6: Pemeliharaan Database & Penanganan Gangguan

### 6.1 Memeriksa Ukuran Database & Tabel di Disk
```sql
-- 1. Ukuran keseluruhan database 'gudang'
SELECT pg_size_pretty(pg_database_size('gudang')) AS ukuran_database;

-- 2. Rincian ukuran disk per tabel (termasuk indeks)
SELECT 
    relname AS nama_tabel,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_ukuran,
    pg_size_pretty(pg_relation_size(relid)) AS ukuran_data,
    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS ukuran_indeks
FROM pg_catalog.pg_statio_user_tables 
ORDER BY pg_total_relation_size(relid) DESC;
```

### 6.2 Memeriksa Koneksi Aktif (*Active Sessions*)
```sql
SELECT 
    pid, 
    usename, 
    client_addr, 
    application_name, 
    state,
    query_start,
    state_change
FROM pg_stat_activity 
WHERE datname = 'gudang';
```

### 6.3 Menghentikan Koneksi Nyangkut / Menggantung (*Kill Idle Sessions*)
Jika ada sesi koneksi backend atau psql lain yang macet atau mengunci tabel:
```sql
-- Putus koneksi spesifik berdasarkan nomor PID tertentu:
SELECT pg_terminate_backend(12345); -- Ganti 12345 dengan PID yang didapat

-- Putus SEMUA koneksi lain ke database gudang (kecuali koneksi psql kita sendiri):
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'gudang' 
  AND pid <> pg_backend_pid();
```

### 6.4 Optimalisasi Performa & Pembersihan (*Vacuum Analyze*)
Jalankan berkala untuk menyegarkan statistik query planner dan membersihkan baris mati (*dead tuples*):
```sql
VACUUM (VERBOSE, ANALYZE) barang;
VACUUM (VERBOSE, ANALYZE) history_barang;
```

---

## Bab 7: Aturan Keselamatan DBA (*Poka-Yoke Safeguards*)

Untuk mencegah kecelakaan data (*accidental data loss*) saat mengoperasikan konsol psql di lingkungan produksi:

1. **Wajib Selalu Menyertakan Klausa `WHERE` pada `UPDATE` dan `DELETE`:**
   - *BAHAYA:* `UPDATE barang SET jumlah = 0;` (Akan mereset SELURUH stok barang di gudang!).
   - *AMAN:* `UPDATE barang SET jumlah = 0 WHERE id = 45;`

2. **Gunakan Transaksi Eksplisit (`BEGIN ... COMMIT / ROLLBACK`):**
   - Sebelum mengeksekusi perintah modifikasi massal, ketik `BEGIN;`.
   - Jalankan query manipulasi data Anda.
   - Periksa dengan query `SELECT` apakah baris yang terdampak sudah benar.
   - Jika puas dan benar, ketik `COMMIT;`.
   - Jika salah ketik atau jumlah baris terdampak tidak sesuai, langsung ketik `ROLLBACK;`.

3. **Gunakan Mode Expanded (`\x`) Sebelum Menampilkan Tabel Lebar:**
   - Selalu gunakan `\x` saat query tabel dengan banyak kolom (`history_barang` atau `barang`) agar tampilan tersusun rapi per baris atribut ke bawah.

4. **Jangan Pernah Menggunakan `DROP TABLE` Secara Sembarangan:**
   - Jika ingin memodifikasi struktur tabel, lakukan pencadangan (*backup*) terlebih dahulu menggunakan skrip otomatis `backup_server.bat` atau snapshot `CREATE TABLE nama_backup AS SELECT * FROM ...;`.

---
*Dokumentasi Teknis Resmi Database Gudang PLTA Saguling - Sub-Unit Pemeliharaan Kontrol & Instrumen.*
