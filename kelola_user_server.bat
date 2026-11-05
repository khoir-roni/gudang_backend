@echo off
title Kelola Pengguna Gudang - PC SERVER (100.119.4.53)
cd /d "%~dp0"
echo ===================================================================
echo   MENGHUBUNGKAN KE PC SERVER GUDANG PLTA SAGULING (100.119.4.53)
echo ===================================================================
ssh -t "server 2@100.119.4.53" "cd D:\gudangWarehouse\gudang_backend; .\.venv\Scripts\python.exe manage_users.py"
pause
