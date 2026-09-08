@echo off
title Pita Detector - Image Origin and AI Detector
color 0b

echo =======================================================
echo          PITA DETECTOR - FORENSIC DETECTOR
echo   Detektor Asal Gambar: HP vs DSLR vs Buatan AI
echo =======================================================
echo.

cd /d "%~dp0"

REM Periksa apakah folder .venv sudah ada
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Membuat virtual environment Python...
    python -m venv .venv
    echo [INFO] Menginstall dependensi...
    .\.venv\Scripts\pip install -r requirements.txt
)

REM Periksa sampel
if not exist "samples\sample_ai.png" (
    echo [INFO] Membuat berkas sampel uji...
    .\.venv\Scripts\python create_samples.py
)

echo [INFO] Membuka antarmuka di browser...
start "" "http://127.0.0.1:8000"

echo [INFO] Menjalankan server lokal di http://127.0.0.1:8000 ...
echo [INFO] Tekan Ctrl+C di terminal ini jika ingin menghentikan server.
echo.

.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000

pause
