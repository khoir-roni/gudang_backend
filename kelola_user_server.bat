@echo off
title Kelola Pengguna Gudang - PC SERVER
cd /d "%~dp0"

echo ===================================================================
echo     SISTEM MANAJEMEN PENGGUNA GUDANG - PC SERVER
echo ===================================================================

set SPECIFIC_HOST=%~1
set TARGET_HOST=
set TARGET_DESC=

if not "%SPECIFIC_HOST%"=="" goto set_manual
goto auto_detect

:set_manual
set TARGET_HOST=%SPECIFIC_HOST%
set "TARGET_DESC=Host Pilihan Manual [%SPECIFIC_HOST%]"
goto connect

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

:connect
echo.
echo ===================================================================
echo   TERHUBUNG VIA : %TARGET_DESC%
echo   HOST TARGET   : %TARGET_HOST%
echo ===================================================================
echo.

ssh -t %TARGET_HOST% "cd D:\gudangWarehouse\gudang_backend; .\.venv\Scripts\python.exe manage_users.py"

pause
