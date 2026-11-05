@echo off
chcp 65001 >nul
title Master Dashboard Kontrol Gudang PLTA Saguling
cd /d "%~dp0"

:menu
cls
echo ===================================================================
echo     PUSAT KONTROL UTAMA SISTEM GUDANG PEMELIHARAAN PLTA SAGULING
echo ===================================================================
echo   [1] Jalankan Backend Flask API (start_Api.bat)
echo   [2] Buka Penjelajah Data Interaktif (jelajah_gudang.bat)
echo   [3] Kelola Pengguna & Hak Akses (kelola_user.bat)
echo   [4] Backup Database Server ke Laptop (backup_server.bat)
echo   [5] Sinkronkan Database Server ke Laptop (sync_db_from_server.bat)
echo   [6] Jalankan Pengujian Otomatis Backend (tests/test_tipe_backend.py)
echo   [7] Buka Buku Panduan PSQL (PANDUAN_PSQL_GUDANG.md)
echo   [0] Keluar
echo ===================================================================
set /p PILIHAN="Pilih menu (0-7): "

if "%PILIHAN%"=="0" exit /b
if "%PILIHAN%"=="1" (
    call "%~dp0start_Api.bat"
    goto menu
)
if "%PILIHAN%"=="2" (
    call "%~dp0jelajah_gudang.bat"
    goto menu
)
if "%PILIHAN%"=="3" (
    call "%~dp0kelola_user.bat"
    goto menu
)
if "%PILIHAN%"=="4" (
    call "%~dp0backup_server.bat"
    pause
    goto menu
)
if "%PILIHAN%"=="5" (
    call "%~dp0sync_db_from_server.bat"
    pause
    goto menu
)
if "%PILIHAN%"=="6" (
    echo.
    echo Menjalankan Pengujian Otomatis Backend...
    echo -------------------------------------------------------------------
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" tests\test_tipe_backend.py
    ) else (
        python tests\test_tipe_backend.py
    )
    echo -------------------------------------------------------------------
    pause
    goto menu
)
if "%PILIHAN%"=="7" (
    if exist "%~dp0PANDUAN_PSQL_GUDANG.md" (
        start "" "%~dp0PANDUAN_PSQL_GUDANG.md"
    ) else (
        echo File PANDUAN_PSQL_GUDANG.md tidak ditemukan.
    )
    goto menu
)

echo Pilihan tidak valid. Silakan coba lagi.
timeout /t 2 >nul
goto menu
