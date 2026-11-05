@echo off
title Sinkronisasi Tools Excel ke PostgreSQL
cd /d "%~dp0"
echo =======================================================
echo Menjalankan Sinkronisasi Tabel Tools ke PostgreSQL...
echo =======================================================
python sync_tools_to_psql.py
echo.
pause
