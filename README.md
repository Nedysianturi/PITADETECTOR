# Pita Detector - Image Origin & AI Detector 🔍🤖📱📷

**Pita Detector** adalah sistem analisis forensik citra digital berbasis web lokal yang dirancang untuk mengidentifikasi dan membedakan asal-usul gambar ke dalam empat kategori utama:
1. 📱 **Kamera Smartphone (HP)**
2. 📷 **Kamera Dedicated (DSLR / Mirrorless)**
3. 💻 **Kamera Laptop & Webcam**
4. 🤖 **Kecerdasan Buatan (Generative AI - Stable Diffusion, Midjourney, DALL-E, Flux, dll.)**

Sistem berjalan **100% mandiri secara offline di komputer lokal Anda** tanpa membutuhkan API eksternal atau koneksi internet.

---

## ⚡ Fitur Utama

- **Analisis Multi-Lapisan (Hybrid Forensics)**:
  - **Lapisan 1 (Metadata & Signatures)**: Memeriksa tag EXIF, TIFF, XMP, MakerNotes, dan chunk metadata AI (prompt, workflow, model checkpoint, C2PA Content Credentials).
  - **Lapisan 2 (Error Level Analysis - ELA)**: Menganalisis perbedaan rasio kompresi JPEG diferensial untuk mendeteksi manipulasi atau uniformitas sintetik AI.
  - **Lapisan 3 (2D Fast Fourier Transform - FFT)**: Memetakan sidik jari frekuensi untuk mendeteksi anomali kisi dekonvolusi (*checkerboard artifacts*) dan cutoff VAE.
  - **Lapisan 4 (Sensor Noise & Optical Halos)**: Mengekstrak residual noise sensor dan rasio sharpening halo untuk membedakan ISP smartphone vs sensor besar Full-Frame/APS-C.
- **Visual Forensics Inspector Interaktif**:
  - Tampilan visual langsung untuk **Foto Asli**, **ELA Heatmap**, **2D FFT Spectrum**, dan **Noise Residual**.
- **Fitur Praktis**:
  - Mendukung **Drag-and-Drop**.
  - Mendukung **Paste Langsung dari Clipboard (<kbd>Ctrl</kbd> + <kbd>V</kbd>)**.
  - Tombol **Quick Sample** untuk menguji sistem seketika dengan 1 klik.

---

## 🚀 Cara Menjalankan

### Cara Paling Mudah (Windows):
Cukup **klik dua kali berkas `start.bat`**.  
Script akan otomatis memeriksa environment, menjalankan server lokal, dan langsung membuka browser Anda ke alamat `http://127.0.0.1:8000`.

### Cara Manual via Terminal:
1. Buka PowerShell / Terminal di folder ini:
   ```powershell
   cd C:\Users\Cipad\.gemini\antigravity-ide\scratch\lens-ai-sentinel
   ```
2. Buat virtual environment (jika belum):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\pip install -r requirements.txt
   ```
3. Jalankan server:
   ```powershell
   .\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
4. Buka browser Anda dan akses:
   ```
   http://127.0.0.1:8000
   ```

---

## 🧪 Menjalankan Pengujian Otomatis

Untuk memastikan seluruh mesin deteksi bekerja akurat:
```powershell
.\.venv\Scripts\python test_analyzer.py
```
Semua sampel uji bawaan (AI, Smartphone, DSLR) akan diuji dan divalidasi probabilitasnya.

---

## 📂 Struktur Proyek

```
lens-ai-sentinel/
├── forensics/
│   ├── __init__.py
│   ├── metadata_engine.py    # Ekstraksi EXIF, C2PA, dan AI prompt chunks
│   ├── ela_engine.py         # Error Level Analysis & heatmap kompresi
│   ├── frequency_engine.py   # 2D Fast Fourier Transform (FFT)
│   ├── noise_engine.py       # Residual noise & rasio penajaman komputasi
│   └── classifier.py         # Algoritma sintesis skor probabilitas
├── static/
│   ├── index.html            # Antarmuka web modern
│   ├── style.css             # Desain dark-mode cyber forensic
│   └── app.js                # Interaktivitas UI & Fetch API
├── samples/                  # Berkas sampel pengujian instan
├── main.py                   # Server FastAPI
├── start.bat                 # Windows one-click launcher
├── requirements.txt          # Dependensi Python
├── create_samples.py         # Generator gambar sampel
└── test_analyzer.py          # Script validasi otomatis
```
