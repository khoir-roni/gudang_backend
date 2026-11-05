@echo off
title Manajemen Pengguna Gudang PLTA Saguling
cd /d "%~dp0"

echo ===================================================================
echo     SISTEM MANAJEMEN PENGGUNA GUDANG PLTA SAGULING
echo ===================================================================
echo  Pilih Database Target:
echo   [1] PC Server (100.119.4.53) - DATA OPERASIONAL RESMI [DEFAULT]
echo   [2] Laptop Lokal (localhost) - Database Pengujian Lokal
echo   [0] Keluar
echo ===================================================================
set /p TARGET="Pilih target (0-2) [Default: 1]: "
if "%TARGET%"=="" set TARGET=1

if "%TARGET%"=="0" exit /b
if "%TARGET%"=="1" (
    echo.
    echo Menghubungkan ke PC Server (100.119.4.53)...
    ssh -t "server 2@100.119.4.53" "cd D:\gudangWarehouse\gudang_backend; .\.venv\Scripts\python.exe manage_users.py"
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

:end
pause
