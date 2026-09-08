from typing import Dict, Any, List
from PIL import Image

# Resolusi baku yang dihasilkan oleh model generator AI (Stable Diffusion, Midjourney, DALL-E, SDXL, Flux)
COMMON_AI_RESOLUTIONS = [
    (512, 512), (768, 768), (1024, 1024), (1536, 1536), (2048, 2048),  # 1:1 Latent Squares
    (832, 1216), (1216, 832),                                          # SDXL Standard
    (1024, 1792), (1792, 1024),                                        # DALL-E 3 16:9 / 9:16
    (896, 1152), (1152, 896),                                          # SDXL 3:4 / 4:3
    (768, 1344), (1344, 768)                                           # SDXL 9:16 / 16:9
]

def classify_image(
    metadata_res: Dict[str, Any],
    ela_res: Dict[str, Any],
    freq_res: Dict[str, Any],
    noise_res: Dict[str, Any],
    image_size: tuple
) -> Dict[str, Any]:
    """
    Sintesis hasil multi-layer forensik citra menjadi probabilitas 5 klasifikasi:
    - 📱 Kamera Smartphone (HP)
    - 📷 Kamera Dedicated (DSLR / Mirrorless)
    - 💻 Kamera Laptop / Webcam
    - 🤖 Buatan AI (Generative AI)
    - 🖥️ Tangkapan Layar (Screenshot)
    """
    w, h = image_size
    aspect_ratio = round(max(w, h) / (min(w, h) + 1e-6), 2)
    megapixels = round((w * h) / 1000000.0, 2)
    
    # Inisialisasi bobot dasar untuk 5 kategori
    score_ai = 4.0
    score_phone = 4.0
    score_camera = 4.0
    score_webcam = 4.0
    score_screenshot = 4.0
    reasons = []
    
    # -------------------------------------------------------------
    # 1. ANALISIS METADATA (Bobot Terkuat jika ada)
    # -------------------------------------------------------------
    ai_sigs = metadata_res.get("ai_signatures_found", [])
    if ai_sigs:
        score_ai += 90.0
        reasons.append(f"**Jejak AI Ditemukan**: Berkas memuat signature/prompt AI terverifikasi ({', '.join(ai_sigs)}).")
        
    device_cat = metadata_res.get("device_category", "unknown")
    if device_cat == "screenshot":
        score_screenshot += 85.0
        reasons.append(f"**Perangkat Tangkapan Layar Terdeteksi**: Metadata/Nama file mengindikasikan software screenshot ({metadata_res.get('software') or 'Screen Capture Tool'}).")
    elif device_cat == "webcam":
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
    # 2. ANALISIS RESOLUSI, ORIENTASI, & ASPEK RASIO
    # -------------------------------------------------------------
    is_screen_res = metadata_res.get("is_screen_resolution", False)
    is_ai_res = (w, h) in COMMON_AI_RESOLUTIONS or (w == h and w in [512, 768, 1024, 1536, 2048])

    if is_ai_res and not metadata_res.get("has_exif"):
        score_ai += 45.0
        reasons.append(f"**Resolusi Standar Generator AI**: Dimensi persis {w}x{h} px adalah format output baku model difusi/AI (Midjourney/DALL-E/Flux/SDXL).")
    elif is_screen_res:
        score_screenshot += 30.0
        reasons.append(f"**Resolusi Standar Layar Komputer/HP**: Dimensi {w}x{h} px persis cocok dengan format monitor desktop atau layar ponsel standar.")

    # Orientasi Vertikal Mobile (Portrait Smartphone: 9:16, 3:4, 19.5:9 Status/Story)
    # HANYA jika bukan resolusi buatan AI simetris 1:1
    is_vertical_mobile = (h > w) and (
        abs(aspect_ratio - 1.78) < 0.18 or  # 9:16 (576x1024, 720x1280, 1080x1920)
        abs(aspect_ratio - 1.33) < 0.18 or  # 3:4 vertical
        abs(aspect_ratio - 2.05) < 0.30     # 18:9 / 19.5:9 / 20:9 layar ponsel modern
    )
    if is_vertical_mobile and not is_screen_res and not is_ai_res:
        score_phone += 28.0
        reasons.append(f"**Format Vertikal Kamera HP**: Dimensi {w}x{h} px (rasio potret {aspect_ratio}:1) adalah format standar jepretan kamera ponsel / WhatsApp / Story.")

    # Resolusi khas Webcam / Laptop: HANYA jika landscape (w > h) karena modul webcam laptop selalu mendatar
    is_webcam_resolution = (w > h) and (w, h) in [
        (1280, 720), (640, 480), (1280, 960), (1920, 1080)
    ]
    if (is_webcam_resolution or (w > h and megapixels <= 2.1 and abs(aspect_ratio - 1.78) < 0.05)) and device_cat != "screenshot" and not is_ai_res:
        score_webcam += 20.0
        reasons.append(f"**Resolusi Standar Laptop/Webcam**: Dimensi landscape {w}x{h} px ({megapixels} MP, 16:9/4:3) adalah format modul video conference.")
    elif abs(aspect_ratio - 1.5) < 0.05 and megapixels >= 8.0:
        # 3:2 adalah rasio standar sensor DSLR/Mirrorless 35mm (cth: 6000x4000)
        score_camera += 20.0
        reasons.append(f"**Rasio 3:2 Asli Fotografi**: Aspek rasio {aspect_ratio} dengan resolusi tinggi ({megapixels} MP) adalah standar emas sensor kamera 35mm DSLR/Mirrorless.")
    elif abs(aspect_ratio - 1.33) < 0.05 and megapixels >= 8.0:
        # 4:3 resolusi tinggi adalah rasio default sensor smartphone modern (cth: 4032x3024 = 12MP)
        score_phone += 18.0
        reasons.append(f"**Rasio 4:3 Sensor Mobile**: Resolusi {megapixels} MP dengan rasio {aspect_ratio} adalah standar default sensor kamera smartphone.")

    # -------------------------------------------------------------
    # 3. ANALISIS FREKUENSI 2D FFT
    # -------------------------------------------------------------
    spectral_anomaly = freq_res.get("spectral_anomaly_score", 0.0)
    high_energy = freq_res.get("high_energy_ratio", 0.0)
    hf_kurt = freq_res.get("hf_kurtosis", 0.0)
    halo_ratio = noise_res.get("halo_ratio", 0.0)
    
    if spectral_anomaly >= 0.4 and not noise_res.get("is_likely_screenshot", False):
        score_ai += 25.0 * spectral_anomaly
        reasons.append(f"**Anomali Spektral Difusi**: Terdeteksi lonjakan frekuensi diskrit (kurtosis {hf_kurt:.1f}) yang konsisten dengan artefak dekonvolusi AI.")
    elif high_energy > 0.18:
        # PENTING: Hanya berikan poin penajaman kamera jika BUKAN resolusi AI (1024x1024 dll),
        # karena teks/tipografi grafis pada poster AI akan menipu metrik high energy & halo ratio
        if halo_ratio > 35.0 and not is_ai_res:
            score_phone += 15.0
        elif halo_ratio < 25.0 and megapixels <= 2.5 and (w > h) and not is_ai_res:
            score_webcam += 12.0
        elif not is_ai_res and not is_vertical_mobile:
            score_camera += 15.0

    # -------------------------------------------------------------
    # 4. ANALISIS NOISE SENSOR & CIRI DIGITAL SCREENSHOT
    # -------------------------------------------------------------
    avg_noise = noise_res.get("avg_noise_std", 0.0)
    edge_energy = noise_res.get("edge_energy", 0.0)
    is_screenshot = noise_res.get("is_likely_screenshot", False)
    screenshot_score = noise_res.get("screenshot_score", 0.0)
    pure_color_ratio = noise_res.get("pure_color_ratio", 0.0)
    is_webcam_optics = noise_res.get("is_likely_webcam_optics", False)
    
    if is_screenshot:
        score_screenshot += 40.0
        reasons.append(f"**Karakteristik Tangkapan Layar**: Zero-noise optik ({avg_noise:.2f}), tepi piksel digital ter-render presisi, dan rasio elemen grafis murni ({pure_color_ratio*100:.1f}%).")
    elif screenshot_score >= 5.0 and not metadata_res.get("has_exif") and not is_ai_res:
        score_screenshot += 25.0
        reasons.append(f"**Ciri Grafis Digital UI**: Skor keseragaman piksel tinggi ({screenshot_score:.1f}) mengindikasikan tampilan antarmuka digital.")
    elif is_ai_res and not metadata_res.get("has_exif"):
        # Gambar resolusi AI tanpa EXIF
        score_ai += 25.0
        reasons.append(f"**Karakteristik Sintetis Citra AI**: Ketiadaan metadata sensor fisik pada format resolusi {w}x{h} px.")
    elif avg_noise < 2.2 and not metadata_res.get("has_exif") and not is_screen_res:
        if spectral_anomaly >= 0.35 or len(ai_sigs) > 0 or is_ai_res:
            score_ai += 25.0
            reasons.append(f"**Absensi Sensor Noise**: Level noise residual sangat rendah ({avg_noise:.2f}), konsisten dengan sintesis digital kecerdasan buatan.")
        elif is_vertical_mobile or (megapixels <= 2.5 and not is_screenshot):
            score_phone += 22.0
            reasons.append(f"**Denoising & Kompresi Medsos**: Noise halus ({avg_noise:.2f}) dengan spektrum frekuensi alami, konsisten dengan pemrosesan ISP ponsel / kompresi WhatsApp.")
        else:
            score_ai += 10.0
    elif is_webcam_optics and (w > h) and not is_ai_res:
        score_webcam += 25.0
        reasons.append(f"**Optik Lensa Webcam/Laptop**: Ditemukan noise indoor ({avg_noise:.2f}) dengan kontras tepi lembut tanpa ISP neural penajaman ekstrem.")
    elif avg_noise >= 3.0 and not is_ai_res:
        if halo_ratio > 34.0:
            score_phone += 22.0
            reasons.append(f"**Sharpening Komputasi Terdeteksi**: Tepi objek memiliki halo penajaman digital agresif (Halo Ratio {halo_ratio:.1f}) khas algoritma ISP ponsel pintar.")
        elif halo_ratio <= 32.0 and megapixels >= 4.0:
            score_camera += 20.0
            reasons.append(f"**Tekstur Grain Sensor Alami**: Distribusi noise Poisson-Gaussian ({avg_noise:.2f}) dengan transisi tepi optik halus tanpa penajaman digital berlebih.")

    # -------------------------------------------------------------
    # 5. ANALISIS ERROR LEVEL ANALYSIS (ELA)
    # -------------------------------------------------------------
    mean_ela = ela_res.get("mean_error", 0.0)
    if mean_ela < 1.6 and not metadata_res.get("has_exif") and not is_screenshot:
        if spectral_anomaly >= 0.35 or len(ai_sigs) > 0 or is_ai_res:
            score_ai += 15.0
            reasons.append(f"**Uniformitas Kompresi Sintetik (ELA)**: Mean error ELA sangat rendah ({mean_ela:.2f}) mengindikasikan citra hasil sintesis digital utuh.")
        elif is_vertical_mobile:
            score_phone += 10.0
    elif mean_ela > 6.5 and halo_ratio > 35.0 and not is_ai_res:
        score_phone += 10.0

    # -------------------------------------------------------------
    # 6. PENGECEKAN KETIADAAN EXIF & MEDIA SOSIAL
    # -------------------------------------------------------------
    if not metadata_res.get("has_exif"):
        if is_screenshot or is_screen_res:
            score_screenshot += 10.0
        elif is_ai_res:
            score_ai += 15.0
        elif is_vertical_mobile:
            # Foto HP di media sosial (WhatsApp/IG) hampir 100% selalu dihapus EXIF-nya oleh server medsos
            score_phone += 18.0
            reasons.append("**Metadata Terhapus Kompresi Medsos**: Ketiadaan EXIF dengan format rasio potret konsisten dengan foto kamera HP yang dikirim melalui aplikasi perpesanan/medsos.")
        elif spectral_anomaly >= 0.35 or len(ai_sigs) > 0:
            score_ai += 10.0
        else:
            score_phone += 8.0
            score_webcam += 4.0

    # -------------------------------------------------------------
    # NORMALISASI PROBABILITAS (5 Kategori)
    # -------------------------------------------------------------
    total = score_ai + score_phone + score_camera + score_webcam + score_screenshot
    prob_ai = round((score_ai / total) * 100, 1)
    prob_phone = round((score_phone / total) * 100, 1)
    prob_camera = round((score_camera / total) * 100, 1)
    prob_webcam = round((score_webcam / total) * 100, 1)
    prob_screenshot = round((score_screenshot / total) * 100, 1)
    
    # Penyesuaian akhir agar total tepat 100%
    diff = round(100.0 - (prob_ai + prob_phone + prob_camera + prob_webcam + prob_screenshot), 1)
    prob_ai += diff
    prob_ai = round(max(0.0, min(100.0, prob_ai)), 1)
    prob_phone = round(max(0.0, min(100.0, prob_phone)), 1)
    prob_camera = round(max(0.0, min(100.0, prob_camera)), 1)
    prob_webcam = round(max(0.0, min(100.0, prob_webcam)), 1)
    prob_screenshot = round(max(0.0, min(100.0, prob_screenshot)), 1)

    # Tentukan pemenang
    scores = [
        ("ai", prob_ai, "Kecerdasan Buatan (Generative AI)", "🤖"),
        ("smartphone", prob_phone, "Kamera Smartphone (HP)", "📱"),
        ("dedicated_camera", prob_camera, "Kamera Dedicated (DSLR/Mirrorless)", "📷"),
        ("webcam", prob_webcam, "Kamera Laptop / Webcam", "💻"),
        ("screenshot", prob_screenshot, "Tangkapan Layar (Screenshot)", "🖥️")
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
            "webcam": prob_webcam,
            "screenshot": prob_screenshot
        },
        "reasons": reasons
    }
