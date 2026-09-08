import io
import base64
import numpy as np
from PIL import Image
from typing import Dict, Any

def analyze_frequency_domain(pil_img: Image.Image) -> Dict[str, Any]:
    """
    Analisis Domain Frekuensi menggunakan 2D Fast Fourier Transform (FFT).
    Model AI Generatif (Latent Diffusion & GAN) memiliki karakteristik spektral khusus,
    seperti artefak kisi frekuensi tinggi (checkerboard spikes) atau cutoff frekuensi VAE.
    """
    # 1. Konversi ke Grayscale dan resize ke ukuran standar forensik 512x512
    gray = pil_img.convert("L").resize((512, 512), Image.Resampling.BILINEAR)
    img_arr = np.array(gray, dtype=np.float32)
    
    # 2. Hitung 2D FFT dan geser frekuensi nol ke tengah
    f_transform = np.fft.fft2(img_arr)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shift)
    
    # Log magnitude spectrum untuk visualisasi
    log_magnitude = np.log1p(magnitude)
    
    # Normalisasi untuk statistik
    mag_normalized = (log_magnitude - np.min(log_magnitude)) / (np.max(log_magnitude) - np.min(log_magnitude) + 1e-6)
    
    # 3. Analisis Band Frekuensi (Rendah, Sedang, Tinggi)
    h, w = 512, 512
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - cx)**2 + (y - cy)**2)
    
    low_freq_mask = dist_from_center <= 40
    mid_freq_mask = (dist_from_center > 40) & (dist_from_center <= 160)
    high_freq_mask = dist_from_center > 160
    
    total_energy = np.sum(magnitude) + 1e-6
    low_energy_ratio = float(np.sum(magnitude[low_freq_mask]) / total_energy)
    mid_energy_ratio = float(np.sum(magnitude[mid_freq_mask]) / total_energy)
    high_energy_ratio = float(np.sum(magnitude[high_freq_mask]) / total_energy)
    
    # 4. Deteksi Artefak Kisi (High Frequency Spikes / Peakiness)
    # Foto optik alami memiliki transisi spektrum yang halus (1/f^alpha law).
    # AI sering memiliki spike frekuensi tajam di pita tinggi akibat arsitektur konvolusi/upsampling.
    high_freq_mag = log_magnitude[high_freq_mask]
    hf_mean = float(np.mean(high_freq_mag))
    hf_std = float(np.std(high_freq_mag))
    hf_kurtosis = float(np.mean(((high_freq_mag - hf_mean) / (hf_std + 1e-6))**4))
    
    # Rasio anomali spektral AI (0.0 s/d 1.0)
    # Jika high frequency energy sangat rendah (terlalu mulus/plastik) atau kurtosis lonjakan tinggi
    spectral_anomaly_score = 0.0
    findings = []
    
    if high_energy_ratio < 0.04:
        spectral_anomaly_score += 0.35
        findings.append(f"Energi frekuensi tinggi sangat rendah ({high_energy_ratio*100:.1f}%), mengindikasikan kehalusan mikro (synthetic smoothing) khas VAE AI.")
    elif high_energy_ratio > 0.30:
        findings.append(f"Energi frekuensi tinggi tinggi ({high_energy_ratio*100:.1f}%), khas tekstur alami sensor optik atau sharpening.")
        
    if hf_kurtosis > 4.5:
        spectral_anomaly_score += 0.40
        findings.append(f"Terdeteksi anomali lonjakan frekuensi diskrit (Kurtosis: {hf_kurtosis:.2f}), pola yang sering ditemukan pada arsitektur difusi AI.")
        
    spectral_anomaly_score = min(1.0, spectral_anomaly_score)

    # 5. Buat Gambar Visual Spektrum FFT (Colormap Sci-fi Cyber Heatmap)
    # Peta warna: Ungu -> Cyan -> Kuning (seperti Inferno/Plasma)
    norm_vis = (mag_normalized * 255).astype(np.uint8)
    
    # Beri tint warna visualizer (RGB)
    r = np.clip(norm_vis * 1.2 - 30, 0, 255).astype(np.uint8)
    g = np.clip(norm_vis * 0.9, 0, 255).astype(np.uint8)
    b = np.clip(255 - norm_vis * 0.8, 0, 255).astype(np.uint8)
    fft_rgb = np.stack([r, g, b], axis=-1)
    
    fft_img = Image.fromarray(fft_rgb)
    thumb_buf = io.BytesIO()
    fft_img.save(thumb_buf, format="PNG")
    fft_b64 = base64.b64encode(thumb_buf.getvalue()).decode("utf-8")
    
    return {
        "low_energy_ratio": round(low_energy_ratio, 4),
        "mid_energy_ratio": round(mid_energy_ratio, 4),
        "high_energy_ratio": round(high_energy_ratio, 4),
        "hf_kurtosis": round(hf_kurtosis, 2),
        "spectral_anomaly_score": round(spectral_anomaly_score, 2),
        "fft_image_b64": f"data:image/png;base64,{fft_b64}",
        "findings": findings
    }
