import io
import base64
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from typing import Dict, Any, Tuple

def perform_ela(pil_img: Image.Image, quality: int = 92, scale: int = 15) -> Dict[str, Any]:
    """
    Melakukan Error Level Analysis (ELA) untuk mendeteksi tingkat kompresi diferensial.
    Gambar buatan AI atau hasil rekayasa digital seringkali menunjukkan tingkat error
    yang berbeda dibandingkan jepretan kamera optik tunggal.
    """
    # Pastikan mode RGB
    rgb_img = pil_img.convert("RGB")
    
    # Simpan ke buffer in-memory dengan JPEG quality tertentu
    buffer = io.BytesIO()
    rgb_img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    
    resaved_img = Image.open(buffer)
    
    # Hitung selisih pixel-wise (absolute difference)
    diff = ImageChops.difference(rgb_img, resaved_img)
    
    # Dapatkan array statistik
    diff_arr = np.array(diff, dtype=np.float32)
    mean_err = float(np.mean(diff_arr))
    std_err = float(np.std(diff_arr))
    max_err = float(np.max(diff_arr))
    
    # Rasio variansi error terhadap mean error (mengukur homogenitas artefak)
    error_uniformity = float(std_err / (mean_err + 1e-6))
    
    # Buat citra visualisasi ELA yang diperkuat (enhanced contrast) untuk inspeksi pengguna
    # Skala error agar terlihat jelas oleh mata manusia
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1
    multiplier = min(scale, 255.0 / max_diff)
    
    enhanced = ImageEnhance.Brightness(diff).enhance(multiplier)
    
    # Simpan visualisasi ELA ke Base64 (max 600px width untuk efisiensi transfer web)
    thumb = enhanced.copy()
    thumb.thumbnail((600, 600))
    thumb_buf = io.BytesIO()
    thumb.save(thumb_buf, format="JPEG", quality=85)
    thumb_b64 = base64.b64encode(thumb_buf.getvalue()).decode("utf-8")
    
    findings = []
    if mean_err < 1.8:
        findings.append(f"Tingkat error ELA sangat rendah ({mean_err:.2f}), mengindikasikan kompresi yang sangat halus atau sintetik.")
    elif mean_err > 8.0:
        findings.append(f"Tingkat error ELA tinggi ({mean_err:.2f}), umum pada gambar kaya tekstur berfrekuensi tinggi atau multi-kompresi.")
        
    return {
        "mean_error": round(mean_err, 3),
        "std_error": round(std_err, 3),
        "max_error": round(max_err, 3),
        "error_uniformity": round(error_uniformity, 3),
        "ela_image_b64": f"data:image/jpeg;base64,{thumb_b64}",
        "findings": findings
    }
