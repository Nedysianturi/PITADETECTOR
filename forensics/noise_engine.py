import io
import base64
import numpy as np
from PIL import Image, ImageFilter
from typing import Dict, Any

def analyze_noise_and_optics(pil_img: Image.Image) -> Dict[str, Any]:
    """
    Menganalisis karakteristik noise sensor, dispersi butiran (grain),
    dan jejak komputasi penajaman (unsharp masking/sharpening halo).
    Membedakan kamera HP (computational HDR + denoising agresif + halo tajam),
    kamera DSLR (noise optik Poisson-Gaussian alami), AI (ketiadaan noise fisik),
    Webcam (noise indoor moderat), dan Screenshot/Desain Grafis (noise nol + piksel murni digital).
    """
    # Resize untuk analisis noise standar
    img = pil_img.convert("RGB")
    w, h = img.size
    scale = min(1.0, 1000.0 / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
        
    arr = np.array(img, dtype=np.float32)
    
    # 1. Ekstraksi Noise Residual (High-pass residual via median/box filter)
    smoothed = img.filter(ImageFilter.BoxBlur(1))
    smooth_arr = np.array(smoothed, dtype=np.float32)
    noise_residual = arr - smooth_arr
    
    # Standar deviasi noise per channel (R, G, B)
    std_r = float(np.std(noise_residual[:, :, 0]))
    std_g = float(np.std(noise_residual[:, :, 1]))
    std_b = float(np.std(noise_residual[:, :, 2]))
    avg_noise_std = float((std_r + std_g + std_b) / 3.0)
    
    # Variansi noise antar channel
    noise_channel_variance = float(np.var([std_r, std_g, std_b]))
    
    # 2. Analisis Ketajaman Tepi & Halo Unsharp Mask
    gray = img.convert("L")
    gray_arr = np.array(gray, dtype=np.float32)
    
    padded = np.pad(gray_arr, 1, mode='edge')
    laplacian = (
        padded[:-2, 1:-1] +
        padded[2:, 1:-1] +
        padded[1:-1, :-2] +
        padded[1:-1, 2:] -
        4 * padded[1:-1, 1:-1]
    )
    
    edge_energy = float(np.var(laplacian))
    p99 = float(np.percentile(np.abs(laplacian), 99.5))
    p50 = float(np.median(np.abs(laplacian)) + 1e-6)
    halo_ratio = float(p99 / p50)

    # ── 3. DETEKSI SCREENSHOT & ELEMEN GRAFIS DIGITAL ───────────────────────
    # (a) Rasio piksel tetangga yang identik mutlak (zero differential gradient)
    h_diff = np.abs(np.diff(arr, axis=1))
    v_diff = np.abs(np.diff(arr, axis=0))
    zero_diff_ratio = float(((h_diff == 0).mean() + (v_diff == 0).mean()) / 2.0)

    # (b) Uniformitas warna blok besar (flat region score)
    row_sample = arr[arr.shape[0] // 2, :, :]
    h_mean_diff = np.abs(np.diff(row_sample, axis=0)).mean()
    col_sample = arr[:, arr.shape[1] // 2, :]
    v_mean_diff = np.abs(np.diff(col_sample, axis=0)).mean()
    flat_region_score = float(1.0 / (1.0 + (h_mean_diff + v_mean_diff) / 2.0 + 1e-6))

    # (c) Deteksi warna khas Web/UI: Pure White (#FFFFFF) & Pure Black (#000000)
    arr_uint8 = np.array(img, dtype=np.uint8)
    white_mask = np.all(arr_uint8 > 248, axis=2)
    black_mask = np.all(arr_uint8 < 8,   axis=2)
    white_ratio = float(white_mask.mean())
    black_ratio = float(black_mask.mean())
    pure_color_ratio = float(white_ratio + black_ratio)

    # (d) Deteksi Saturasi Sintetis Vektor Grafis / Poster
    hsv_arr = np.array(img.convert("HSV"))
    sat_ratio = float((hsv_arr[:, :, 1] > 180).mean())

    # Elemen grafis/tipografi digital memiliki kontras tepi ekstrim (font/vektor)
    is_graphic_elements = bool((p99 > 75.0 and sat_ratio > 0.08) or (p99 > 115.0))

    # (e) Perhitungan skor screenshot terpadu
    is_likely_screenshot = False
    screenshot_score = 0.0

    if zero_diff_ratio > 0.75:
        screenshot_score += 5.0
    elif zero_diff_ratio > 0.45:
        screenshot_score += 2.5

    if pure_color_ratio > 0.25:
        screenshot_score += 3.0
    elif pure_color_ratio > 0.08:
        screenshot_score += 1.5

    if flat_region_score > 0.15:
        screenshot_score += 2.0

    if noise_channel_variance < 0.2:
        screenshot_score += 1.0

    if (zero_diff_ratio > 0.50 and pure_color_ratio > 0.10) or (zero_diff_ratio > 0.80):
        is_likely_screenshot = True
    elif screenshot_score >= 6.5 and zero_diff_ratio > 0.40:
        is_likely_screenshot = True

    # ── 4. Klasifikasi optik ──────────────────────────────────────────────────
    findings = []
    is_likely_smartphone_optics = False
    is_likely_dslr_optics       = False
    is_likely_webcam_optics     = False
    is_likely_ai_noise          = False

    if is_likely_screenshot:
        findings.append(
            f"Karakteristik tangkapan layar digital terdeteksi: rasio piksel identik "
            f"({zero_diff_ratio*100:.1f}%), ketiadaan noise sensor foton alami, "
            f"dan dominasi warna UI murni ({pure_color_ratio*100:.1f}%)."
        )
    elif is_graphic_elements:
        findings.append(
            f"Terdeteksi elemen grafis digital/tipografi berkontras sangat tinggi (Laplacian p99: {p99:.1f}) "
            f"dan saturasi warna sintetis ({sat_ratio*100:.1f}%), mengindikasikan poster/desain grafis atau komposit AI."
        )
    elif halo_ratio > 38.0 and avg_noise_std < 7.0 and not is_graphic_elements:
        is_likely_smartphone_optics = True
        findings.append(
            f"Terdeteksi sharpening halo tinggi (Rasio: {halo_ratio:.1f}), "
            "karakteristik kuat dari computational photography smartphone."
        )
    elif avg_noise_std >= 2.5 and halo_ratio < 28.0 and edge_energy < 150.0:
        is_likely_webcam_optics = True
        findings.append(
            f"Karakteristik optik webcam/laptop terdeteksi: noise indoor moderat "
            f"({avg_noise_std:.2f}) dengan kontras tepi lembut tanpa ISP sharpening agresif."
        )
    elif avg_noise_std >= 3.8 and halo_ratio <= 35.0:
        is_likely_dslr_optics = True
        findings.append(
            f"Dispersi noise seimbang ({avg_noise_std:.2f}) dengan transisi tepi optik alami "
            "(bebas over-sharpening), karakteristik sensor besar kamera DSLR/Mirrorless."
        )
    elif avg_noise_std < 2.2:
        is_likely_ai_noise = True
        findings.append(
            f"Level residual noise sangat mendekati nol ({avg_noise_std:.2f}), "
            "mengindikasikan ketiadaan sensor fisik (sintesis digital/AI)."
        )
        
    # 5. Visualisasi Noise Residual
    vis_noise = np.clip((noise_residual * 5.0) + 128.0, 0, 255).astype(np.uint8)
    noise_img = Image.fromarray(vis_noise)
    noise_img.thumbnail((600, 600))
    thumb_buf = io.BytesIO()
    noise_img.save(thumb_buf, format="JPEG", quality=85)
    noise_b64 = base64.b64encode(thumb_buf.getvalue()).decode("utf-8")
    
    return {
        "avg_noise_std":            round(avg_noise_std, 3),
        "channel_std": {
            "r": round(std_r, 3),
            "g": round(std_g, 3),
            "b": round(std_b, 3)
        },
        "edge_energy":              round(edge_energy, 2),
        "halo_ratio":               round(halo_ratio, 2),
        "lap_p99":                  round(p99, 1),
        "sat_ratio":                round(sat_ratio, 4),
        "zero_diff_ratio":          round(zero_diff_ratio, 4),
        "pure_color_ratio":         round(pure_color_ratio, 4),
        "flat_region_score":        round(flat_region_score, 4),
        "screenshot_score":         round(screenshot_score, 2),
        "noise_channel_variance":   round(noise_channel_variance, 4),
        "is_likely_screenshot":     is_likely_screenshot,
        "is_graphic_elements":      is_graphic_elements,
        "is_likely_smartphone_optics": is_likely_smartphone_optics,
        "is_likely_dslr_optics":    is_likely_dslr_optics,
        "is_likely_webcam_optics":  is_likely_webcam_optics,
        "is_likely_ai_noise":       is_likely_ai_noise,
        "noise_image_b64":          f"data:image/jpeg;base64,{noise_b64}",
        "findings":                 findings
    }
