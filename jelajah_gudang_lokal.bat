@echo off
chcp 65001 >nul
title Penjelajah Data Gudang - LAPTOP LOKAL
cd /d "%~dp0"

echo ===================================================================
echo     PENJELAJAH DATA GUDANG PEMELIHARAAN - LAPTOP LOKAL
echo ===================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" explorer_gudang.py --target local
) else (
    python explorer_gudang.py --target local
)

pause
