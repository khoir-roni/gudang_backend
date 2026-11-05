@echo off
title Kelola Pengguna Gudang - LAPTOP LOKAL
cd /d "%~dp0"
echo ===================================================================
echo   MANAJEMEN PENGGUNA - LAPTOP LOKAL (LOCALHOST)
echo ===================================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" manage_users.py
) else (
    python manage_users.py
)
pause
