import io
import base64
import numpy as np
from PIL import Image, ImageFilter
from typing import Dict, Any

def analyze_noise_and_optics(pil_img: Image.Image) -> Dict[str, Any]:
    """
    Menganalisis karakteristik noise sensor, dispersi butiran (grain),
    dan jejak komputasi penajaman (unsharp masking/sharpening halo).
    Membedakan kamera HP (computational HDR + denoising agresif + halo tajam)
    dengan kamera DSLR (noise optik Poisson-Gaussian alami) dan AI (ketiadaan noise fisik).
    """
    # Resize untuk analisis noise standar
    img = pil_img.convert("RGB")
    w, h = img.size
    scale = min(1.0, 1000.0 / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
        
    arr = np.array(img, dtype=np.float32)
    
    # 1. Ekstraksi Noise Residual (High-pass residual via median/box filter)
    # Foto asli dikurangi versi smooth = sisa noise
    smoothed = img.filter(ImageFilter.BoxBlur(1))
    smooth_arr = np.array(smoothed, dtype=np.float32)
    noise_residual = arr - smooth_arr
    
    # Standar deviasi noise per channel (R, G, B)
    std_r = float(np.std(noise_residual[:, :, 0]))
    std_g = float(np.std(noise_residual[:, :, 1]))
    std_b = float(np.std(noise_residual[:, :, 2]))
    avg_noise_std = float((std_r + std_g + std_b) / 3.0)
    
    # Variansi noise antar channel (Kamera fisik sensor Bayer memiliki korelasi noise tertentu)
    noise_channel_variance = float(np.var([std_r, std_g, std_b]))
    
    # 2. Analisis Ketajaman Tepi & Halo Unsharp Mask (Computational Photography vs Optical Blur)
    # Gunakan filter Laplacian untuk mendeteksi gradien tepi
    gray = img.convert("L")
    gray_arr = np.array(gray, dtype=np.float32)
    
    # Kernel Laplacian 3x3 sederhana
    # [ 0,  1,  0]
    # [ 1, -4,  1]
    # [ 0,  1,  0]
    padded = np.pad(gray_arr, 1, mode='edge')
    laplacian = (
        padded[:-2, 1:-1] +
        padded[2:, 1:-1] +
        padded[1:-1, :-2] +
        padded[1:-1, 2:] -
        4 * padded[1:-1, 1:-1]
    )
    
    edge_energy = float(np.var(laplacian))
    
    # Hitung rasio overshoot / haloing (nilai ekstrim pada tepi dibanding rata-rata kontras)
    p99 = float(np.percentile(np.abs(laplacian), 99.5))
    p50 = float(np.median(np.abs(laplacian)) + 1e-6)
    halo_ratio = float(p99 / p50)
    
    findings = []
    
    # Evaluasi pola
    # Smartphone: noise residual rendah di area rata tapi halo ratio sangat tinggi (akibat software sharpening)
    # Webcam: noise moderat/tinggi tapi ketajaman tepi rendah (lensa plastik fixed-focus tanpa neural ISP)
    # DSLR: noise seimbang dengan rentang dinamis tinggi dan optik tajam alami
    # AI: noise sangat rendah / artificial smoothness
    is_likely_smartphone_optics = False
    is_likely_dslr_optics = False
    is_likely_webcam_optics = False
    is_likely_ai_noise = False
    
    if halo_ratio > 38.0 and avg_noise_std < 7.0:
        is_likely_smartphone_optics = True
        findings.append(f"Terdeteksi sharpening halo tinggi (Rasio: {halo_ratio:.1f}), karakteristik kuat dari computational photography smartphone.")
    elif avg_noise_std >= 2.5 and halo_ratio < 28.0 and edge_energy < 150.0:
        is_likely_webcam_optics = True
        findings.append(f"Karakteristik optik webcam/laptop terdeteksi: noise indoor moderat ({avg_noise_std:.2f}) dengan kontras tepi lembut tanpa ISP sharpening agresif.")
    elif avg_noise_std >= 3.8 and halo_ratio <= 35.0:
        is_likely_dslr_optics = True
        findings.append(f"Dispersi noise seimbang ({avg_noise_std:.2f}) dengan transisi tepi optik alami (bebas over-sharpening), karakteristik sensor besar kamera DSLR/Mirrorless.")
    elif avg_noise_std < 2.2:
        is_likely_ai_noise = True
        findings.append(f"Level residual noise sangat mendekati nol ({avg_noise_std:.2f}), mengindikasikan ketiadaan sensor fisik (sintesis digital/AI).")
        
    # 3. Visualisasi Noise Residual (ditingkatkan kontrasnya untuk UI)
    # Skala noise ke 128 tengah
    vis_noise = np.clip((noise_residual * 5.0) + 128.0, 0, 255).astype(np.uint8)
    noise_img = Image.fromarray(vis_noise)
    noise_img.thumbnail((600, 600))
    thumb_buf = io.BytesIO()
    noise_img.save(thumb_buf, format="JPEG", quality=85)
    noise_b64 = base64.b64encode(thumb_buf.getvalue()).decode("utf-8")
    
    return {
        "avg_noise_std": round(avg_noise_std, 3),
        "channel_std": {
            "r": round(std_r, 3),
            "g": round(std_g, 3),
            "b": round(std_b, 3)
        },
        "edge_energy": round(edge_energy, 2),
        "halo_ratio": round(halo_ratio, 2),
        "is_likely_smartphone_optics": is_likely_smartphone_optics,
        "is_likely_dslr_optics": is_likely_dslr_optics,
        "is_likely_webcam_optics": is_likely_webcam_optics,
        "is_likely_ai_noise": is_likely_ai_noise,
        "noise_image_b64": f"data:image/jpeg;base64,{noise_b64}",
        "findings": findings
    }
