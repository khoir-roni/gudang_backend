@echo off
title Manajemen Pengguna Gudang PLTA Saguling
cd /d "%~dp0"

echo ===================================================================
echo     SISTEM MANAJEMEN PENGGUNA GUDANG PLTA SAGULING
echo ===================================================================
echo  Pilih Database Target:
echo   [1] PC Server [Auto-Detect: Tailscale / Cloudflare / LAN] - DEFAULT
echo   [2] Laptop Lokal [localhost] - Database Pengujian Lokal
echo   [3] PC Server via Tailscale VPN [100.119.4.53]
echo   [4] PC Server via Cloudflare Tunnel [gudangapp-server2]
echo   [5] PC Server via Jaringan LAN Lokal [gudangapp-lokal]
echo   [0] Keluar
echo ===================================================================
set /p TARGET="Pilih target (0-5) [Default: 1]: "
if "%TARGET%"=="" set TARGET=1

if "%TARGET%"=="0" exit /b
if "%TARGET%"=="1" (
    call "%~dp0kelola_user_server.bat"
    goto end
)
if "%TARGET%"=="2" (
    echo.
    echo Menjalankan di Database Laptop Lokal...
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" manage_users.py
    ) else (
        python manage_users.py
    )
    goto end
)
if "%TARGET%"=="3" (
    call "%~dp0kelola_user_server.bat" 100.119.4.53
    goto end
)
if "%TARGET%"=="4" (
    call "%~dp0kelola_user_server.bat" gudangapp-server2
    goto end
)
if "%TARGET%"=="5" (
    call "%~dp0kelola_user_server.bat" gudangapp-lokal
    goto end
)

:end
pause
