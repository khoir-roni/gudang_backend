@echo off
title Sinkronisasi Database Gudang - Server ke Laptop
cd /d "%~dp0"

echo ===================================================================
echo      SINKRONISASI DATABASE GUDANG (SERVER -^> LAPTOP LOKAL)
echo ===================================================================
echo  PERINGATAN:
echo  Proses ini akan menimpa database 'gudang' di LAPTOP LOKAL
echo  dengan salinan data terbaru dari PC SERVER.
echo  Database lokal saat ini akan otomatis dicadangkan (safety snapshot).
echo ===================================================================
echo.

set /p CONFIRM="Lanjutkan sinkronisasi? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo [BATAL] Operasi sinkronisasi dibatalkan oleh pengguna.
    goto end
)

echo.
echo [1/6] Mendeteksi jalur koneksi SSH ke PC Server...
set TARGET_HOST=
set TARGET_DESC=

ssh -o BatchMode=yes -o ConnectTimeout=3 100.119.4.53 exit >nul 2>&1
if not errorlevel 1 (
    set TARGET_HOST=100.119.4.53
    set "TARGET_DESC=Tailscale VPN [100.119.4.53]"
    goto host_found
)

ssh -o BatchMode=yes -o ConnectTimeout=3 gudangapp-server2 exit >nul 2>&1
if not errorlevel 1 (
    set TARGET_HOST=gudangapp-server2
    set "TARGET_DESC=Cloudflare Tunnel [ssh.gudangapp-hki.my.id]"
    goto host_found
)

ssh -o BatchMode=yes -o ConnectTimeout=2 gudangapp-lokal exit >nul 2>&1
if not errorlevel 1 (
    set TARGET_HOST=gudangapp-lokal
    set "TARGET_DESC=Jaringan LAN Lokal [192.168.31.58]"
    goto host_found
)

:host_found
if "%TARGET_HOST%"=="" (
    echo  [PERINGATAN] Menggunakan fallback Tailscale [100.119.4.53]...
    set TARGET_HOST=100.119.4.53
    set "TARGET_DESC=Tailscale Fallback [100.119.4.53]"
)

echo  Terhubung via : %TARGET_DESC%
echo.

if not exist backups mkdir backups

rem Generate timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set LDT=%%I
set TS=%LDT:~0,8%_%LDT:~8,6%

echo [2/6] Membuat safety snapshot database laptop lokal...
set PGPASSWORD=123456
pg_dump -U postgres -d gudang -f "backups\backup_gudang_laptop_before_sync_%TS%.sql" >nul 2>&1
if errorlevel 1 (
    echo  [CATATAN] Database laptop belum ada atau gagal di-dump, melanjutkan...
) else (
    echo  Safety snapshot tersimpan di: backups\backup_gudang_laptop_before_sync_%TS%.sql
)

echo.
echo [3/6] Meminta PC Server melakukan pg_dump database 'gudang'...
ssh %TARGET_HOST% "powershell -Command \"$env:PGPASSWORD='123456'; if (-not (Test-Path 'D:\gudangWarehouse\gudang_backend\backups')) { New-Item -ItemType Directory -Path 'D:\gudangWarehouse\gudang_backend\backups' -Force | Out-Null }; & 'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe' -U postgres -d gudang -f 'D:\gudangWarehouse\gudang_backend\backups\backup_gudang_server_latest.sql'\""
if errorlevel 1 (
    echo  [ERROR] Gagal melakukan dump database di PC Server! Periksa koneksi atau layanan PostgreSQL di server.
    goto error
)

echo.
echo [4/6] Mengunduh berkas dump dari PC Server via SCP...
scp %TARGET_HOST%:D:/gudangWarehouse/gudang_backend/backups/backup_gudang_server_latest.sql backups\backup_gudang_server_latest.sql
if errorlevel 1 (
    echo  [ERROR] Gagal mentransfer berkas dump dari server!
    goto error
)

echo.
echo [5/6] Me-reset dan me-restore database 'gudang' di laptop lokal...
psql -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'gudang' AND pid <> pg_backend_pid();" >nul 2>&1
dropdb -U postgres --if-exists gudang >nul 2>&1
createdb -U postgres gudang
if errorlevel 1 (
    echo  [ERROR] Gagal membuat ulang database 'gudang' di lokal!
    goto error
)

psql -U postgres -d gudang -f "backups\backup_gudang_server_latest.sql" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Terjadi kesalahan saat me-restore data ke database 'gudang' lokal!
    goto error
)

echo.
echo [6/6] Memverifikasi data hasil sinkronisasi...
echo -------------------------------------------------------------------
for /f "tokens=*" %%a in ('psql -U postgres -d gudang -t -A -c "SELECT count(*) FROM barang;"') do set TOTAL_BARANG=%%a
for /f "tokens=*" %%a in ('psql -U postgres -d gudang -t -A -c "SELECT count(*) FROM barang WHERE tipe = 'material';"') do set TOTAL_MATERIAL=%%a
for /f "tokens=*" %%a in ('psql -U postgres -d gudang -t -A -c "SELECT count(*) FROM barang WHERE tipe = 'tool';"') do set TOTAL_TOOL=%%a
for /f "tokens=*" %%a in ('psql -U postgres -d gudang -t -A -c "SELECT count(*) FROM barang WHERE tgl_kalibrasi IS NOT NULL;"') do set TOTAL_KALIBRASI=%%a
for /f "tokens=*" %%a in ('psql -U postgres -d gudang -t -A -c "SELECT count(*) FROM users;"') do set TOTAL_USERS=%%a
for /f "tokens=*" %%a in ('psql -U postgres -d gudang -t -A -c "SELECT count(*) FROM history_login;"') do set TOTAL_LOGIN=%%a

echo  Total Barang      : %TOTAL_BARANG% item
echo    - Material      : %TOTAL_MATERIAL% item
echo    - Tools         : %TOTAL_TOOL% item
echo    - Ada Kalibrasi : %TOTAL_KALIBRASI% instrumen
echo  Total Pengguna    : %TOTAL_USERS% akun
echo  Total Hist. Login : %TOTAL_LOGIN% log
echo -------------------------------------------------------------------
echo.
echo ===================================================================
echo  [SUKSES] SINKRONISASI DATABASE SERVER KE LAPTOP BERHASIL 100%%!
echo ===================================================================
goto end

:error
echo.
echo ===================================================================
echo  [GAGAL] Sinkronisasi tidak selesai. Periksa pesan kesalahan di atas.
echo ===================================================================

:end
echo.
pause
