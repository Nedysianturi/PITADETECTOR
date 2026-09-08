import os
import io
import numpy as np
from PIL import Image, PngImagePlugin
import piexif

def create_samples():
    os.makedirs("samples", exist_ok=True)
    
    # 1. Sampel AI Image (PNG dengan metadata Stable Diffusion & pola halus difusi)
    print("Membuat sampel AI...")
    w, h = 512, 512
    x_grid, y_grid = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    
    r = np.clip(128 + 120 * np.sin(x_grid / 35.0) * np.cos(y_grid / 35.0), 0, 255).astype(np.uint8)
    g = np.clip(120 + 100 * np.sin((x_grid + y_grid) / 45.0), 0, 255).astype(np.uint8)
    b = np.clip(180 + 70 * np.cos((x_grid - y_grid) / 30.0), 0, 255).astype(np.uint8)
    ai_img = Image.fromarray(np.stack([r, g, b], axis=-1))
    
    png_info = PngImagePlugin.PngInfo()
    prompt_metadata = (
        "cyberpunk futuristic city at dusk, glowing neon, ultra detailed, octane render, 8k\n"
        "Steps: 30, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 128938472, Size: 512x512, "
        "Model: dreamshaper_v8"
    )
    png_info.add_text("parameters", prompt_metadata)
    png_info.add_text("Software", "Stable Diffusion WebUI")
    ai_img.save("samples/sample_ai.png", pnginfo=png_info)

    # 2. Sampel Smartphone (JPEG 4:3 dengan EXIF Apple iPhone 15 Pro)
    print("Membuat sampel Smartphone...")
    sw, sh = 800, 600
    sx, sy = np.meshgrid(np.arange(sw, dtype=np.float32), np.arange(sh, dtype=np.float32))
    base_color = np.zeros((sh, sw, 3), dtype=np.float32)
    base_color[:, :, 0] = 70 + (sy / sh) * 100
    base_color[:, :, 1] = 120 + (sx / sw) * 60
    base_color[:, :, 2] = 210 - (sy / sh) * 40
    # Tambah noise sensor kecil smartphone
    phone_noise = np.random.normal(0, 1.8, (sh, sw, 3))
    phone_arr = np.clip(base_color + phone_noise, 0, 255).astype(np.uint8)
    phone_img = Image.fromarray(phone_arr)

    # EXIF Smartphone
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "Apple",
            piexif.ImageIFD.Model: "iPhone 15 Pro",
            piexif.ImageIFD.Software: "iOS 17.5.1",
            piexif.ImageIFD.DateTime: "2026:08:14 14:22:10"
        },
        "Exif": {
            piexif.ExifIFD.FocalLength: (676, 100), # 6.76mm
            piexif.ExifIFD.FocalLengthIn35mmFilm: 24, # 24mm equivalent (crop factor 3.55x)
            piexif.ExifIFD.FNumber: (178, 100), # f/1.78
            piexif.ExifIFD.ISOSpeedRatings: 80,
            piexif.ExifIFD.ExposureTime: (1, 240),
            piexif.ExifIFD.LensModel: "iPhone 15 Pro back triple camera 6.76mm f/1.78"
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    phone_img.save("samples/sample_smartphone.jpg", "jpeg", quality=95, exif=exif_bytes)

    # 3. Sampel DSLR / Dedicated Camera (JPEG 3:2 dengan EXIF Sony Alpha A7 IV)
    print("Membuat sampel DSLR...")
    dw, dh = 900, 600
    dx, dy = np.meshgrid(np.arange(dw, dtype=np.float32), np.arange(dh, dtype=np.float32))
    dslr_base = np.zeros((dh, dw, 3), dtype=np.float32)
    dslr_base[:, :, 0] = 50 + (dy / dh) * 140
    dslr_base[:, :, 1] = 80 + (dx / dw) * 80
    dslr_base[:, :, 2] = 110 + (dy / dh) * 70
    # Noise alami sensor Full-Frame
    dslr_noise = np.random.normal(0, 4.5, (dh, dw, 3))
    dslr_arr = np.clip(dslr_base + dslr_noise, 0, 255).astype(np.uint8)
    dslr_img = Image.fromarray(dslr_arr)

    # EXIF DSLR
    dslr_exif = {
        "0th": {
            piexif.ImageIFD.Make: "Sony",
            piexif.ImageIFD.Model: "ILCE-7M4",
            piexif.ImageIFD.Software: "ILCE-7M4 v2.01",
            piexif.ImageIFD.DateTime: "2026:07:22 18:45:30"
        },
        "Exif": {
            piexif.ExifIFD.FocalLength: (500, 10), # 50.0mm
            piexif.ExifIFD.FocalLengthIn35mmFilm: 50, # 50mm Full-Frame (crop factor 1.0x)
            piexif.ExifIFD.FNumber: (18, 10), # f/1.8
            piexif.ExifIFD.ISOSpeedRatings: 400,
            piexif.ExifIFD.ExposureTime: (1, 1000),
            piexif.ExifIFD.LensModel: "FE 50mm F1.8"
        }
    }
    dslr_exif_bytes = piexif.dump(dslr_exif)
    dslr_img.save("samples/sample_dslr.jpg", "jpeg", quality=98, exif=dslr_exif_bytes)

    # 4. Sampel Kamera Laptop / Webcam (JPEG 16:9 1280x720 dengan EXIF Logitech C920 / Integrated Camera)
    print("Membuat sampel Laptop / Webcam...")
    ww, wh = 1280, 720
    wx, wy = np.meshgrid(np.arange(ww, dtype=np.float32), np.arange(wh, dtype=np.float32))
    webcam_base = np.zeros((wh, ww, 3), dtype=np.float32)
    webcam_base[:, :, 0] = 90 + (wy / wh) * 60
    webcam_base[:, :, 1] = 95 + (wx / ww) * 50
    webcam_base[:, :, 2] = 115 + (wy / wh) * 40
    # Noise indoor webcam (sensor kecil, SNR moderat, tanpa penajaman agresif)
    webcam_noise = np.random.normal(0, 3.2, (wh, ww, 3))
    webcam_arr = np.clip(webcam_base + webcam_noise, 0, 255).astype(np.uint8)
    webcam_img = Image.fromarray(webcam_arr)

    webcam_exif = {
        "0th": {
            piexif.ImageIFD.Make: "Logitech",
            piexif.ImageIFD.Model: "HD Pro Webcam C920",
            piexif.ImageIFD.Software: "Windows Camera 10.2104.5.0",
            piexif.ImageIFD.DateTime: "2026:09:01 10:15:22"
        },
        "Exif": {
            piexif.ExifIFD.FocalLength: (367, 100), # 3.67mm
            piexif.ExifIFD.FNumber: (20, 10), # f/2.0
            piexif.ExifIFD.ISOSpeedRatings: 250,
            piexif.ExifIFD.ExposureTime: (1, 60)
        }
    }
    webcam_exif_bytes = piexif.dump(webcam_exif)
    webcam_img.save("samples/sample_webcam.jpg", "jpeg", quality=88, exif=webcam_exif_bytes)
    print("Sampel berhasil dibuat di folder samples/!")

if __name__ == "__main__":
    create_samples()
