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
    Sintesis hasil multi-layer forensik citra menjadi probabilitas 5 klasifikasi:
    - 📱 Kamera Smartphone (HP)
    - 📷 Kamera Dedicated (DSLR / Mirrorless)
    - 💻 Kamera Laptop / Webcam
    - 🤖 Buatan AI (Generative AI)
    - 🖥️ Tangkapan Layar / Desain Grafis (Screenshot)
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

    # Ambil metrik grafis digital dari noise_res
    is_graphic = noise_res.get("is_graphic_elements", False)
    sat_ratio = noise_res.get("sat_ratio", 0.0)
    lap_p99 = noise_res.get("lap_p99", 0.0)
    zero_diff_ratio = noise_res.get("zero_diff_ratio", 0.0)
    
    # -------------------------------------------------------------
    # 1. ANALISIS METADATA (Bobot Terkuat jika ada)
    # -------------------------------------------------------------
    ai_sigs = metadata_res.get("ai_signatures_found", [])
    if ai_sigs:
        score_ai += 90.0
        reasons.append(f"**Jejak AI Ditemukan**: Berkas memuat signature/prompt AI terverifikasi ({', '.join(ai_sigs)}).")
        
    device_cat = metadata_res.get("device_category", "unknown")
    has_exif = metadata_res.get("has_exif", False)
    has_camera_hardware_exif = bool(has_exif and device_cat in ["dedicated_camera", "smartphone", "webcam"])

    is_canva_sig = metadata_res.get("is_canva_signature", False)
    is_canva_fn = metadata_res.get("is_canva_filename", False)
    canva_preset = metadata_res.get("canva_preset_name")
    is_canva_detected = False

    if device_cat == "canva" or is_canva_sig:
        score_screenshot += 110.0
        is_canva_detected = True
        reasons.append("**Platform Desain Canva Terverifikasi**: Metadata berkas memuat tanda tangan digital resmi / header ekspor platform Canva (canva.com).")
    elif device_cat == "screenshot":
        score_screenshot += 85.0
        reasons.append(f"**Perangkat Tangkapan Layar Terdeteksi**: Metadata/Nama file mengindikasikan software screenshot ({metadata_res.get('software') or 'Screen Capture Tool'}).")
    elif device_cat == "webcam":
        score_webcam += 120.0
        reasons.append(f"**Perangkat Webcam / Laptop Terdeteksi**: EXIF/Software mencatat {metadata_res.get('make')} {metadata_res.get('model')} {metadata_res.get('software')}".strip())
    elif device_cat == "smartphone":
        score_phone += 140.0
        reasons.append(f"**Hardware Smartphone Terdeteksi**: EXIF mencatat perangkat {metadata_res.get('make')} {metadata_res.get('model')}.")
        if metadata_res.get("f_number") or metadata_res.get("exposure_time") or metadata_res.get("iso"):
            score_phone += 15.0
            reasons.append(f"**Parameter Sensor Ponsel**: f/{metadata_res.get('f_number') or '-'}, ISO {metadata_res.get('iso') or '-'}, Shutter {metadata_res.get('exposure_time') or '-'}s.")
    elif device_cat == "dedicated_camera":
        score_camera += 140.0
        reasons.append(f"**Kamera Profesional Terdeteksi**: EXIF mencatat bodi {metadata_res.get('make')} {metadata_res.get('model')}.")
        if metadata_res.get("lens_model"):
            score_camera += 30.0
            reasons.append(f"**Optik Lensa Fisik**: Lensa eksternal {metadata_res.get('lens_model')}.")
        if metadata_res.get("f_number") or metadata_res.get("exposure_time") or metadata_res.get("iso"):
            score_camera += 15.0
            reasons.append(f"**Parameter Eksposur Kamera**: f/{metadata_res.get('f_number') or '-'}, ISO {metadata_res.get('iso') or '-'}, Shutter {metadata_res.get('exposure_time') or '-'}s.")
        if megapixels >= 10.0:
            score_camera += 25.0
            reasons.append(f"**Resolusi Sensor Besar**: Format {w}x{h} px ({megapixels} MP) khas sensor optik kamera resolusi tinggi.")

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
    if is_screen_res and not has_camera_hardware_exif:
        score_screenshot += 30.0
        reasons.append(f"**Resolusi Standar Layar Komputer/HP**: Dimensi {w}x{h} px persis cocok dengan format monitor desktop atau layar ponsel standar.")

    # Deteksi format template kanvas Canva standar
    if canva_preset and not has_camera_hardware_exif:
        if is_canva_fn or is_canva_sig:
            score_screenshot += 40.0
            is_canva_detected = True
            reasons.append(f"**Template Kanvas Canva Terverifikasi**: Format dimensi {w}x{h} px cocok dengan template {canva_preset} resmi Canva.")
        elif device_cat != "screenshot" and not is_screen_res and is_graphic:
            score_screenshot += 35.0
            is_canva_detected = True
            reasons.append(f"**Template Kanvas Canva Terdeteksi**: Format dimensi {w}x{h} px cocok dengan template kanvas {canva_preset} standar Canva.")
        elif device_cat != "screenshot" and (w, h) in [(1080, 1080), (1024, 1024), (1080, 1350), (1587, 2245), (2480, 3508), (1414, 2000)]:
            score_screenshot += 30.0
            if is_graphic:
                is_canva_detected = True
                reasons.append(f"**Template Kanvas Canva Terdeteksi**: Format dimensi {w}x{h} px cocok dengan template kanvas {canva_preset} standar Canva.")

    # Orientasi Vertikal Mobile (Portrait Smartphone: 9:16, 3:4, 19.5:9 Status/Story)
    is_vertical_mobile = (h > w) and (
        abs(aspect_ratio - 1.78) < 0.18 or  # 9:16 (576x1024, 720x1280, 1080x1920)
        abs(aspect_ratio - 1.33) < 0.18 or  # 3:4 vertical
        abs(aspect_ratio - 2.05) < 0.30     # 18:9 / 19.5:9 / 20:9 layar ponsel modern
    )
    if is_vertical_mobile and not is_screen_res and not is_graphic and not is_canva_detected:
        score_phone += 28.0
        reasons.append(f"**Format Vertikal Kamera HP**: Dimensi {w}x{h} px (rasio potret {aspect_ratio}:1) adalah format standar jepretan kamera ponsel / WhatsApp / Story.")

    # Resolusi khas Webcam / Laptop: HANYA jika landscape (w > h) karena modul webcam laptop selalu mendatar
    is_webcam_resolution = (w > h) and (w, h) in [
        (1280, 720), (640, 480), (1280, 960), (1920, 1080)
    ]
    if (is_webcam_resolution or (w > h and megapixels <= 2.1 and abs(aspect_ratio - 1.78) < 0.05)) and device_cat != "screenshot" and not is_graphic and not has_camera_hardware_exif and not is_canva_detected:
        score_webcam += 20.0
        reasons.append(f"**Resolusi Standar Laptop/Webcam**: Dimensi landscape {w}x{h} px ({megapixels} MP, 16:9/4:3) adalah format modul video conference.")
    elif w == h and not is_graphic and not is_canva_detected and (w in [512, 768, 1024, 1536, 2048]):
        # Format 1:1 simetris tanpa teks adalah ciri khas generator model difusi
        score_ai += 25.0
        reasons.append(f"**Resolusi Standar Generator AI**: Dimensi simetris persis {w}x{h} px sangat umum pada checkpoint model difusi.")
    elif abs(aspect_ratio - 1.5) < 0.05 and megapixels >= 8.0 and (not is_graphic or has_camera_hardware_exif):
        # 3:2 adalah rasio standar sensor DSLR/Mirrorless 35mm (cth: 6000x4000)
        score_camera += 20.0
        reasons.append(f"**Rasio 3:2 Asli Fotografi**: Aspek rasio {aspect_ratio} dengan resolusi tinggi ({megapixels} MP) adalah standar emas sensor kamera 35mm DSLR/Mirrorless.")
    elif abs(aspect_ratio - 1.33) < 0.05 and megapixels >= 8.0 and (not is_graphic or has_camera_hardware_exif):
        # 4:3 resolusi tinggi adalah rasio default sensor smartphone modern (cth: 4032x3024 = 12MP)
        score_phone += 18.0
        reasons.append(f"**Rasio 4:3 Sensor Mobile**: Resolusi {megapixels} MP dengan rasio {aspect_ratio} adalah standar default sensor kamera smartphone.")

    # -------------------------------------------------------------
    # 3. ANALISIS FREKUENSI 2D FFT
    # -------------------------------------------------------------
    spectral_anomaly = freq_res.get("spectral_anomaly_score", 0.0)
    high_energy = freq_res.get("high_energy_ratio", 0.0)
    hf_kurt = freq_res.get("hf_kurtosis", 0.0)
    
    if spectral_anomaly >= 0.4 and not noise_res.get("is_likely_screenshot", False):
        score_ai += 25.0 * spectral_anomaly
        reasons.append(f"**Anomali Spektral Difusi**: Terdeteksi lonjakan frekuensi diskrit (kurtosis {hf_kurt:.1f}) yang konsisten dengan artefak dekonvolusi AI.")
    elif high_energy > 0.18 and not is_graphic and not is_canva_detected:
        # Sensor fisik kaya frekuensi tinggi alami
        if noise_res.get("halo_ratio", 0) > 35.0:
            score_phone += 15.0
        elif noise_res.get("halo_ratio", 0) < 25.0 and megapixels <= 2.5 and (w > h):
            score_webcam += 12.0
        else:
            score_camera += 15.0

    # -------------------------------------------------------------
    # 4. ANALISIS NOISE SENSOR & DETEKSI ELEMEN GRAFIS / POSTER / CANVA
    # -------------------------------------------------------------
    avg_noise = noise_res.get("avg_noise_std", 0.0)
    halo_ratio = noise_res.get("halo_ratio", 0.0)
    edge_energy = noise_res.get("edge_energy", 0.0)
    is_screenshot = noise_res.get("is_likely_screenshot", False)
    screenshot_score = noise_res.get("screenshot_score", 0.0)
    pure_color_ratio = noise_res.get("pure_color_ratio", 0.0)
    is_webcam_optics = noise_res.get("is_likely_webcam_optics", False)

    # A. Penanganan Khusus Gambar Grafis / Desain Poster / Flyer / Banner Promosi / Canva
    if is_graphic:
        if len(ai_sigs) > 0 or spectral_anomaly >= 0.40:
            score_ai += 75.0
            reasons.append("**Generasi AI Terverifikasi**: Ditemukan jejak/anomali generator AI pada berkas desain.")
        elif not has_camera_hardware_exif:
            if is_canva_detected or is_canva_fn or is_canva_sig or (canva_preset and device_cat != "screenshot" and not is_screen_res):
                score_screenshot += 95.0
                is_canva_detected = True
                reasons.append(f"**Desain Grafis Canva Terdeteksi**: Tata letak digital Canva memuat tipografi teks berkontras tinggi (Laplacian p99 {lap_p99:.1f}), blok warna sintetis ({sat_ratio*100:.1f}%), dan elemen grafis vektor non-kamera.")
                reasons.append("**Bukan Jepretan Kamera Fisik**: Citra merupakan hasil tata letak desain grafis digital Canva, bukan foto langsung dari sensor optik kamera.")
            else:
                # Poster promosi, flyer Canva/Photoshop, atau tangkapan layar dokumen tanpa EXIF kamera fisik
                score_screenshot += 85.0
                reasons.append(f"**Desain Grafis / Poster Digital Terdeteksi**: Memuat tipografi teks digital berkontras tinggi (Laplacian p99 {lap_p99:.1f}), blok warna sintetis ({sat_ratio*100:.1f}%), dan elemen tata letak promosi non-kamera.")
                reasons.append("**Bukan Jepretan Kamera Fisik**: Citra merupakan hasil tata letak digital (Canva / Desain Poster / Tangkapan Media Sosial), bukan foto langsung dari sensor kamera optik.")
        else:
            # Objek nyata dalam bidikan kamera (spanduk panggung, banner backdrop, teks pameran)
            reasons.append(f"**Objek Spanduk / Teks Terdeteksi**: Terdeteksi elemen tulisan/spanduk panggung pada latar bidikan (Laplacian p99 {lap_p99:.1f}), ditangkap langsung oleh sensor kamera optik.")
    elif is_screenshot and not has_camera_hardware_exif:
        score_screenshot += 40.0
        reasons.append(f"**Karakteristik Tangkapan Layar**: Zero-noise optik ({avg_noise:.2f}), tepi piksel digital ter-render presisi, dan rasio elemen grafis murni ({pure_color_ratio*100:.1f}%).")
    elif screenshot_score >= 5.0 and not has_exif:
        score_screenshot += 25.0
        reasons.append(f"**Ciri Grafis Digital UI**: Skor keseragaman piksel tinggi ({screenshot_score:.1f}) mengindikasikan tampilan antarmuka digital.")
    elif avg_noise < 2.2 and not has_exif and not is_screen_res:
        # Pembeda krusial AI vs Foto Terkompresi Medsos:
        if spectral_anomaly >= 0.35 or len(ai_sigs) > 0 or (w == h and w in [512, 768, 1024]):
            score_ai += 25.0
            reasons.append(f"**Absensi Sensor Noise**: Level noise residual sangat rendah ({avg_noise:.2f}), konsisten dengan sintesis digital kecerdasan buatan.")
        elif is_vertical_mobile or (megapixels <= 2.5 and not is_screenshot):
            score_phone += 22.0
            reasons.append(f"**Denoising & Kompresi Medsos**: Noise halus ({avg_noise:.2f}) dengan spektrum frekuensi alami, konsisten dengan pemrosesan ISP ponsel / kompresi WhatsApp.")
        else:
            score_ai += 10.0
    elif is_webcam_optics and (w > h) and not has_camera_hardware_exif:
        score_webcam += 25.0
        reasons.append(f"**Optik Lensa Webcam/Laptop**: Ditemukan noise indoor ({avg_noise:.2f}) dengan kontras tepi lembut tanpa ISP neural penajaman ekstrem.")
    elif avg_noise >= 3.0 and not is_graphic:
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
    if mean_ela < 1.6 and not has_exif and not is_screenshot and not is_graphic:
        if spectral_anomaly >= 0.35 or len(ai_sigs) > 0 or (w == h and w in [512, 768, 1024]):
            score_ai += 12.0
        elif is_vertical_mobile:
            score_phone += 10.0
    elif mean_ela > 6.5 and halo_ratio > 35.0 and not is_graphic:
        score_phone += 10.0

    # -------------------------------------------------------------
    # 6. PENGECEKAN KETIADAAN EXIF & MEDIA SOSIAL
    # -------------------------------------------------------------
    if not has_exif:
        if is_screenshot or is_screen_res or is_graphic:
            score_screenshot += 10.0
        elif is_vertical_mobile:
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
    if (is_graphic or is_screenshot) and not has_camera_hardware_exif:
        prob_screenshot += diff
    elif has_camera_hardware_exif:
        if device_cat == "dedicated_camera":
            prob_camera += diff
        elif device_cat == "smartphone":
            prob_phone += diff
        elif device_cat == "webcam":
            prob_webcam += diff
        else:
            prob_phone += diff
    elif is_vertical_mobile:
        prob_phone += diff
    else:
        prob_ai += diff

    prob_ai = round(max(0.0, min(100.0, prob_ai)), 1)
    prob_phone = round(max(0.0, min(100.0, prob_phone)), 1)
    prob_camera = round(max(0.0, min(100.0, prob_camera)), 1)
    prob_webcam = round(max(0.0, min(100.0, prob_webcam)), 1)
    prob_screenshot = round(max(0.0, min(100.0, prob_screenshot)), 1)

    # Tentukan pemenang
    screenshot_label = "Desain Grafis Canva (canva.com)" if is_canva_detected else "Tangkapan Layar / Desain Grafis"
    screenshot_icon = "🎨" if is_canva_detected else "🖥️"

    scores = [
        ("ai", prob_ai, "Kecerdasan Buatan (Generative AI)", "🤖"),
        ("smartphone", prob_phone, "Kamera Smartphone (HP)", "📱"),
        ("dedicated_camera", prob_camera, "Kamera Dedicated (DSLR/Mirrorless)", "📷"),
        ("webcam", prob_webcam, "Kamera Laptop / Webcam", "💻"),
        ("screenshot", prob_screenshot, screenshot_label, screenshot_icon)
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    top_cat, top_prob, top_label, top_icon = scores[0]

    confidence = "Tinggi" if top_prob >= 70.0 else ("Sedang" if top_prob >= 45.0 else "Rendah")

    return {
        "verdict": top_cat,
        "verdict_label": top_label,
        "verdict_icon": top_icon,
        "is_canva_detected": is_canva_detected,
        "canva_preset": canva_preset,
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
