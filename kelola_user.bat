@echo off
title Kelola Pengguna Gudang Saguling
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" manage_users.py
) else (
    python manage_users.py
)
pause
