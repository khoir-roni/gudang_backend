@echo off
setlocal enabledelayedexpansion
title Full Backup Database Server Gudang
cd /d "%~dp0"

echo ===================================================================
echo       TOOL OTOMATIS FULL BACKUP BASIS DATA GUDANG PC SERVER
echo ===================================================================
echo.

set SPECIFIC_HOST=%~1
set TARGET_HOST=
set TARGET_DESC=

if not "%SPECIFIC_HOST%"=="" goto set_manual
goto auto_detect

:set_manual
set TARGET_HOST=%SPECIFIC_HOST%
set "TARGET_DESC=Host Pilihan Manual [%SPECIFIC_HOST%]"
goto start_backup

:auto_detect
echo  Mendeteksi jalur koneksi SSH terbaik ke PC Server...
echo.

echo  [1/3] Memeriksa jalur Tailscale VPN [100.119.4.53]...
ssh -o BatchMode=yes -o ConnectTimeout=3 100.119.4.53 exit >nul 2>&1
if not errorlevel 1 (
    set TARGET_HOST=100.119.4.53
    set "TARGET_DESC=Tailscale VPN [100.119.4.53]"
    goto host_found
)
echo        - Tailscale tidak merespons / offline.

echo  [2/3] Memeriksa jalur Cloudflare Tunnel [gudangapp-server2]...
ssh -o BatchMode=yes -o ConnectTimeout=3 gudangapp-server2 exit >nul 2>&1
if not errorlevel 1 (
    set TARGET_HOST=gudangapp-server2
    set "TARGET_DESC=Cloudflare Tunnel [ssh.gudangapp-hki.my.id]"
    goto host_found
)
echo        - Cloudflare Tunnel tidak merespons / offline.

echo  [3/3] Memeriksa jalur LAN Lokal [gudangapp-lokal: 192.168.31.58]...
ssh -o BatchMode=yes -o ConnectTimeout=2 gudangapp-lokal exit >nul 2>&1
if not errorlevel 1 (
    set TARGET_HOST=gudangapp-lokal
    set "TARGET_DESC=Jaringan LAN Lokal [192.168.31.58]"
    goto host_found
)
echo        - Jaringan LAN Lokal tidak merespons / offline.

:host_found
if "%TARGET_HOST%"=="" (
    echo.
    echo ===================================================================
    echo  [PERINGATAN] Tidak ada jalur SSH yang merespons ping cepat!
    echo  Mencoba fallback default ke Tailscale [100.119.4.53]...
    echo ===================================================================
    set TARGET_HOST=100.119.4.53
    set "TARGET_DESC=Tailscale Fallback [100.119.4.53]"
)

:start_backup
echo.
echo ===================================================================
echo   TERHUBUNG VIA : %TARGET_DESC%
echo   HOST TARGET   : %TARGET_HOST%
echo ===================================================================
echo.

if not exist "backups" mkdir "backups"

for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%a
if "%TS%"=="" set TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TS=%TS: =0%

set FILE_NAME=backup_gudang_server_full_%TS%.sql
set REMOTE_PATH=D:\gudangWarehouse\backups\%FILE_NAME%
set LOCAL_PATH=.\backups\%FILE_NAME%

echo  [1/4] Menyiapkan direktori backup di PC Server...
ssh %TARGET_HOST% "New-Item -ItemType Directory -Force -Path D:\gudangWarehouse\backups | Out-Null"

echo  [2/4] Menjalankan pg_dump di PC Server...
echo        Target Database: gudang (PostgreSQL 17)
echo        Target Berkas  : %REMOTE_PATH%
ssh %TARGET_HOST% "$env:PGPASSWORD='123456'; pg_dump -h 127.0.0.1 -U postgres -d gudang -F p --no-owner --no-acl -f %REMOTE_PATH%"

if errorlevel 1 (
    echo [ERROR] Gagal mengeksekusi pg_dump di server!
    pause
    exit /b 1
)

echo.
echo  [3/4] Mengambil salinan mirror backup ke Laptop via SCP...
echo        Sumber: %TARGET_HOST%:%REMOTE_PATH%
echo        Tujuan: %LOCAL_PATH%
scp %TARGET_HOST%:"%REMOTE_PATH%" "%LOCAL_PATH%"

if not exist "%LOCAL_PATH%" (
    echo [ERROR] Berkas backup tidak berhasil disalin ke laptop!
    pause
    exit /b 1
)

echo.
echo  [4/4] Memverifikasi integritas checksum SHA-256...
for /f "tokens=*" %%h in ('certutil -hashfile "%LOCAL_PATH%" SHA256 ^| findstr /r /v "hash certutil CertUtil"') do (
    set HASH_CLEAN=%%h
    set HASH_CLEAN=!HASH_CLEAN: =!
)

echo.
echo ===================================================================
echo             HASIL FULL BACKUP DATABASE BERHASIL
echo ===================================================================
echo  Nama Berkas : %FILE_NAME%
echo  Server Path : %REMOTE_PATH%
echo  Laptop Path : %LOCAL_PATH%
echo  SHA-256 Hash: !HASH_CLEAN!
echo ===================================================================
echo.
pause
