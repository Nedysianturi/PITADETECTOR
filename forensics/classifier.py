from typing import Dict, Any, List
from PIL import Image

def classify_image(
    metadata_res: Dict[str, Any],
    ela_res: Dict[str, Any],
    freq_res: Dict[str, Any],
    noise_res: Dict[str, Any],
    image_size: tuple
) -> Dict[str, Any]:
    """
    Sintesis hasil multi-layer forensik citra menjadi probabilitas klasifikasi:
    - 📱 Kamera Smartphone (HP)
    - 📷 Kamera Dedicated (DSLR / Mirrorless)
    - 💻 Kamera Laptop / Webcam
    - 🤖 Buatan AI (Generative AI)
    """
    w, h = image_size
    aspect_ratio = round(max(w, h) / (min(w, h) + 1e-6), 2)
    megapixels = round((w * h) / 1000000.0, 2)
    
    # Inisialisasi bobot dasar
    score_ai = 4.0
    score_phone = 4.0
    score_camera = 4.0
    score_webcam = 4.0
    reasons = []
    
    # -------------------------------------------------------------
    # 1. ANALISIS METADATA (Bobot Terkuat jika ada)
    # -------------------------------------------------------------
    ai_sigs = metadata_res.get("ai_signatures_found", [])
    if ai_sigs:
        score_ai += 90.0
        reasons.append(f"**Jejak AI Ditemukan**: Berkas memuat signature/prompt AI terverifikasi ({', '.join(ai_sigs)}).")
        
    device_cat = metadata_res.get("device_category", "unknown")
    if device_cat == "webcam":
        score_webcam += 75.0
        reasons.append(f"**Perangkat Webcam / Laptop Terdeteksi**: EXIF/Software mencatat {metadata_res.get('make')} {metadata_res.get('model')} {metadata_res.get('software')}".strip())
    elif device_cat == "smartphone":
        score_phone += 70.0
        reasons.append(f"**Hardware Smartphone Terdeteksi**: EXIF mencatat perangkat {metadata_res.get('make')} {metadata_res.get('model')}.")
    elif device_cat == "dedicated_camera":
        score_camera += 70.0
        reasons.append(f"**Kamera Profesional Terdeteksi**: EXIF mencatat bodi {metadata_res.get('make')} {metadata_res.get('model')}.")
        if metadata_res.get("lens_model"):
            reasons.append(f"**Optik Lensa Fisik**: Lensa eksternal {metadata_res.get('lens_model')}.")

    crop_factor = metadata_res.get("crop_factor")
    if crop_factor:
        if crop_factor >= 3.5:
            score_phone += 15.0
            reasons.append(f"**Karakteristik Sensor Kecil**: Rasio crop factor {crop_factor}x khas modul sensor mobile smartphone.")
        elif crop_factor <= 2.2:
            score_camera += 20.0
            reasons.append(f"**Karakteristik Sensor Besar**: Rasio crop factor {crop_factor}x khas sensor Full-Frame/APS-C.")

    # -------------------------------------------------------------
    # 2. ANALISIS KETIADAAN EXIF & METADATA STRIPPED
    # -------------------------------------------------------------
    if not metadata_res.get("has_exif"):
        score_ai += 10.0
        score_webcam += 6.0
        reasons.append("**Metadata EXIF Tidak Ditemukan**: Umum pada gambar generasi AI, kamera laptop sederhana tanpa EXIF writer, atau gambar kompresi medsos.")

    # -------------------------------------------------------------
    # 3. ANALISIS ASPEK RASIO & RESOLUSI
    # -------------------------------------------------------------
    # Resolusi khas Webcam / Laptop (720p: 1280x720, 1080p: 1920x1080, VGA: 640x480)
    is_webcam_resolution = (w, h) in [
        (1280, 720), (720, 1280),
        (1920, 1080), (1080, 1920),
        (640, 480), (480, 640),
        (1280, 960), (960, 1280)
    ]
    if is_webcam_resolution or (megapixels <= 2.1 and abs(aspect_ratio - 1.78) < 0.05):
        score_webcam += 28.0
        reasons.append(f"**Resolusi Standar Laptop/Webcam**: Dimensi {w}x{h} px ({megapixels} MP, 16:9/4:3) adalah format standar modul webcam/video conference.")
    elif w == h and w in [512, 768, 1024, 1536, 2048]:
        # AI klasik sering menghasilkan 1:1 persis (1024x1024, 512x512)
        score_ai += 25.0
        reasons.append(f"**Resolusi Standar Generator AI**: Dimensi simetris persis {w}x{h} px sangat umum pada checkpoint model difusi.")
    elif abs(aspect_ratio - 1.5) < 0.05 and megapixels >= 8.0:
        # 3:2 adalah rasio standar sensor DSLR/Mirrorless 35mm (cth: 6000x4000)
        score_camera += 20.0
        reasons.append(f"**Rasio 3:2 Asli Fotografi**: Aspek rasio {aspect_ratio} dengan resolusi tinggi ({megapixels} MP) adalah standar emas sensor kamera 35mm DSLR/Mirrorless.")
    elif abs(aspect_ratio - 1.33) < 0.05 and megapixels >= 8.0:
        # 4:3 resolusi tinggi adalah rasio default sensor smartphone modern (cth: 4032x3024 = 12MP)
        score_phone += 18.0
        reasons.append(f"**Rasio 4:3 Sensor Mobile**: Resolusi {megapixels} MP dengan rasio {aspect_ratio} adalah standar default sensor kamera smartphone.")

    # -------------------------------------------------------------
    # 4. ANALISIS FREKUENSI 2D FFT
    # -------------------------------------------------------------
    spectral_anomaly = freq_res.get("spectral_anomaly_score", 0.0)
    high_energy = freq_res.get("high_energy_ratio", 0.0)
    hf_kurt = freq_res.get("hf_kurtosis", 0.0)
    
    if spectral_anomaly >= 0.4:
        score_ai += 25.0 * spectral_anomaly
        reasons.append(f"**Anomali Spektral Difusi**: Terdeteksi lonjakan frekuensi diskrit (kurtosis {hf_kurt:.1f}) yang konsisten dengan artefak dekonvolusi AI.")
    elif high_energy > 0.18:
        # Sensor fisik kaya frekuensi tinggi alami
        if noise_res.get("halo_ratio", 0) > 35.0:
            score_phone += 15.0
        elif noise_res.get("halo_ratio", 0) < 25.0 and megapixels <= 2.5:
            score_webcam += 12.0
        else:
            score_camera += 15.0

    # -------------------------------------------------------------
    # 5. ANALISIS NOISE SENSOR & RESIDUAL
    # -------------------------------------------------------------
    avg_noise = noise_res.get("avg_noise_std", 0.0)
    halo_ratio = noise_res.get("halo_ratio", 0.0)
    edge_energy = noise_res.get("edge_energy", 0.0)
    is_webcam_optics = noise_res.get("is_likely_webcam_optics", False)
    
    if avg_noise < 2.2 and not metadata_res.get("has_exif"):
        score_ai += 22.0
        reasons.append(f"**Absensi Sensor Noise**: Level noise residual sangat rendah ({avg_noise:.2f}), tidak menunjukkan jejak termal sensor silikon fisik.")
    elif is_webcam_optics:
        score_webcam += 25.0
        reasons.append(f"**Optik Lensa Webcam/Laptop**: Ditemukan noise indoor ({avg_noise:.2f}) dengan kontras tepi lembut tanpa ISP neural penajaman ekstrem.")
    elif avg_noise >= 3.5:
        if halo_ratio > 36.0:
            score_phone += 22.0
            reasons.append(f"**Sharpening Komputasi Terdeteksi**: Tepi objek memiliki halo penajaman digital agresif (Halo Ratio {halo_ratio:.1f}) khas algoritma ISP ponsel pintar.")
        elif halo_ratio <= 32.0 and megapixels >= 5.0:
            score_camera += 20.0
            reasons.append(f"**Tekstur Grain Sensor Alami**: Distribusi noise Poisson-Gaussian ({avg_noise:.2f}) dengan transisi tepi optik halus tanpa penajaman digital berlebih.")

    # -------------------------------------------------------------
    # 6. ANALISIS ERROR LEVEL ANALYSIS (ELA)
    # -------------------------------------------------------------
    mean_ela = ela_res.get("mean_error", 0.0)
    if mean_ela < 1.6 and not metadata_res.get("has_exif"):
        score_ai += 12.0
    elif mean_ela > 6.5 and halo_ratio > 35.0:
        score_phone += 10.0

    # -------------------------------------------------------------
    # NORMALISASI PROBABILITAS (4 Kategori)
    # -------------------------------------------------------------
    total = score_ai + score_phone + score_camera + score_webcam
    prob_ai = round((score_ai / total) * 100, 1)
    prob_phone = round((score_phone / total) * 100, 1)
    prob_camera = round((score_camera / total) * 100, 1)
    prob_webcam = round((score_webcam / total) * 100, 1)
    
    # Penyesuaian akhir agar total tepat 100%
    diff = round(100.0 - (prob_ai + prob_phone + prob_camera + prob_webcam), 1)
    prob_ai += diff
    prob_ai = round(max(0.0, min(100.0, prob_ai)), 1)
    prob_phone = round(max(0.0, min(100.0, prob_phone)), 1)
    prob_camera = round(max(0.0, min(100.0, prob_camera)), 1)
    prob_webcam = round(max(0.0, min(100.0, prob_webcam)), 1)

    # Tentukan pemenang
    scores = [
        ("ai", prob_ai, "Kecerdasan Buatan (Generative AI)", "🤖"),
        ("smartphone", prob_phone, "Kamera Smartphone (HP)", "📱"),
        ("dedicated_camera", prob_camera, "Kamera Dedicated (DSLR/Mirrorless)", "📷"),
        ("webcam", prob_webcam, "Kamera Laptop / Webcam", "💻")
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    top_cat, top_prob, top_label, top_icon = scores[0]

    confidence = "Tinggi" if top_prob >= 70.0 else ("Sedang" if top_prob >= 45.0 else "Rendah")

    return {
        "verdict": top_cat,
        "verdict_label": top_label,
        "verdict_icon": top_icon,
        "top_probability": top_prob,
        "confidence": confidence,
        "probabilities": {
            "ai": prob_ai,
            "smartphone": prob_phone,
            "dedicated_camera": prob_camera,
            "webcam": prob_webcam
        },
        "reasons": reasons
    }
