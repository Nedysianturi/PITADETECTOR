import os
import sys
from PIL import Image
from main import process_image_pipeline

def run_tests():
    print("==================================================")
    print(" MENJALANKAN PENGUJIAN OTOMATIS PITA DETECTOR")
    print("==================================================")
    
    samples_to_test = [
        ("samples/sample_ai.png", "ai", "Kecerdasan Buatan"),
        ("samples/sample_smartphone.jpg", "smartphone", "Kamera Smartphone"),
        ("samples/sample_dslr.jpg", "dedicated_camera", "Kamera Dedicated"),
        ("samples/sample_webcam.jpg", "webcam", "Kamera Laptop / Webcam"),
        ("samples/sample_screenshot.png", "screenshot", "Screenshot / Layar"),
        ("samples/sample_canva.jpg", "screenshot", "Desain Grafis Canva")
    ]
    
    all_passed = True

    for filepath, expected_verdict, label in samples_to_test:
        if not os.path.exists(filepath):
            print(f"[FAIL] Berkas {filepath} tidak ditemukan!")
            all_passed = False
            continue
            
        with open(filepath, "rb") as f:
            data = f.read()
            
        res = process_image_pipeline(data, filename=os.path.basename(filepath))
        verdict = res["classification"]["verdict"]
        top_prob = res["classification"]["top_probability"]
        probs = res["classification"]["probabilities"]
        
        status = "[PASS]" if verdict == expected_verdict else "[FAIL]"
        if verdict != expected_verdict:
            all_passed = False
            
        print(f"\n{status} Pengujian: {label} ({filepath})")
        print(f"       Vonis Aktual   : {verdict} ({res['classification']['verdict_label']})")
        print(f"       Probabilitas   : AI={probs['ai']}%, HP={probs['smartphone']}%, DSLR={probs['dedicated_camera']}%, Webcam={probs.get('webcam', 0)}%, Screenshot={probs.get('screenshot', 0)}%")
        print(f"       Alasan Utama   : {res['classification']['reasons'][:2]}")
        print(f"       Dimensi/Format : {res['dimensions']} / {res['format']}")
        print(f"       Metrik Forensik: ELA Mean={res['ela']['mean_error']}, Noise STD={res['noise']['avg_noise_std']}, Halo={res['noise']['halo_ratio']}")

    print("\n--------------------------------------------------")
    if all_passed:
        print(">> SEMUA PENGUJIAN OTOMATIS BERHASIL DENGAN SEMPURNA! <<")
    else:
        print(">> BEBERAPA PENGUJIAN GAGAL, PERIKSA OUTPUT DI ATAS! <<")
    print("--------------------------------------------------")

if __name__ == "__main__":
    run_tests()
