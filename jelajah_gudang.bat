@echo off
chcp 65001 >nul
title Penjelajah Data Gudang PLTA Saguling
cd /d "%~dp0"

echo ===================================================================
echo       PENJELAJAH DATA GUDANG PEMELIHARAAN PLTA SAGULING
echo ===================================================================
echo  Pilih Target Database:
echo   [1] PC Server [Auto-Detect: Tailscale / Cloudflare / LAN] - DEFAULT
echo   [2] Laptop Lokal [localhost:5432] - Database Pengujian Lokal
echo   [3] Mode Audit Komparasi (Laptop vs PC Server Side-by-Side)
echo   [4] PC Server via Tailscale VPN [100.119.4.53]
echo   [5] PC Server via Cloudflare Tunnel [gudangapp-server2]
echo   [6] PC Server via Jaringan LAN Lokal [gudangapp-lokal]
echo   [0] Keluar
echo ===================================================================
set /p TARGET="Pilih target (0-6) [Default: 1]: "
if "%TARGET%"=="" set TARGET=1

if "%TARGET%"=="0" exit /b
if "%TARGET%"=="1" (
    call "%~dp0jelajah_gudang_server.bat"
    goto end
)
if "%TARGET%"=="2" (
    call "%~dp0jelajah_gudang_lokal.bat"
    goto end
)
if "%TARGET%"=="3" (
    echo.
    echo Menjalankan Audit Komparasi Side-by-Side...
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" explorer_gudang.py --compare
    ) else (
        python explorer_gudang.py --compare
    )
    goto end
)
if "%TARGET%"=="4" (
    call "%~dp0jelajah_gudang_server.bat" 100.119.4.53
    goto end
)
if "%TARGET%"=="5" (
    call "%~dp0jelajah_gudang_server.bat" gudangapp-server2
    goto end
)
if "%TARGET%"=="6" (
    call "%~dp0jelajah_gudang_server.bat" gudangapp-lokal
    goto end
)

:end
pause
