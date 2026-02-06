@echo off
echo Starting Ngrok for Gudang Warehouse...
REM Asumsi ngrok sudah ada di PATH (via Chocolatey). 
REM Jika belum, tambahkan: cd C:\ProgramData\chocolatey\bin
ngrok http --url=more-golden-teal.ngrok-free.app 5000