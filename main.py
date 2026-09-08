import os
import io
import base64
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from forensics.metadata_engine import analyze_metadata
from forensics.ela_engine import perform_ela
from forensics.frequency_engine import analyze_frequency_domain
from forensics.noise_engine import analyze_noise_and_optics
from forensics.classifier import classify_image

app = FastAPI(
    title="Pita Detector - Image Origin & AI Detector",
    description="Digital image forensics API detecting Smartphone Camera, DSLR/Mirrorless, and AI-Generated images.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

def process_image_pipeline(image_bytes: bytes, filename: str = "image.jpg") -> dict:
    """Menjalankan full forensic pipeline pada raw image bytes"""
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File bukan format citra yang valid: {str(e)}")

    orig_format = pil_img.format or "UNKNOWN"
    orig_size = pil_img.size
    
    # 1. Pipeline Analisis Forensik
    metadata_res = analyze_metadata(image_bytes, pil_img, filename=filename)
    ela_res = perform_ela(pil_img)
    freq_res = analyze_frequency_domain(pil_img)
    noise_res = analyze_noise_and_optics(pil_img)
    
    # 2. Sintesis Klasifikasi
    classification_res = classify_image(
        metadata_res=metadata_res,
        ela_res=ela_res,
        freq_res=freq_res,
        noise_res=noise_res,
        image_size=orig_size
    )

    # 3. Buat Thumbnail Asli (Base64) untuk UI
    thumb = pil_img.copy()
    thumb.thumbnail((600, 600))
    thumb_buf = io.BytesIO()
    thumb.convert("RGB").save(thumb_buf, format="JPEG", quality=85)
    thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(thumb_buf.getvalue()).decode('utf-8')}"

    return {
        "filename": filename,
        "format": orig_format,
        "dimensions": f"{orig_size[0]} x {orig_size[1]} px",
        "file_size_kb": round(len(image_bytes) / 1024.0, 1),
        "original_thumb_b64": thumb_b64,
        "classification": classification_res,
        "metadata": metadata_res,
        "ela": ela_res,
        "frequency": freq_res,
        "noise": noise_res
    }

@app.post("/api/analyze")
async def analyze_uploaded_file(file: UploadFile = File(...)):
    """Endpoint untuk upload dan analisis berkas gambar"""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Berkas kosong.")
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran berkas melebihi batas 25MB.")
    
    return process_image_pipeline(contents, filename=file.filename or "uploaded_image.jpg")

@app.post("/api/live-capture")
async def analyze_live_capture(request: dict):
    """Endpoint khusus untuk jepretan live dari webcam browser (base64 JPEG)"""
    import base64 as b64_mod
    data_url = request.get("image_data", "")
    if not data_url:
        raise HTTPException(status_code=400, detail="Data gambar kosong.")
    # Strip prefix data:image/jpeg;base64,
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    try:
        image_bytes = b64_mod.b64decode(data_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Format base64 tidak valid.")
    return process_image_pipeline(image_bytes, filename="live_webcam_capture.jpg")

@app.get("/api/samples")
async def list_samples():
    """Daftar sampel bawaan untuk pengujian instan"""
    samples = [
        {
            "id": "ai",
            "name": "Sampel AI (Stable Diffusion)",
            "description": "Gambar sintetis dengan prompt chunk dan pola spektrum difusi",
            "filename": "sample_ai.png",
            "icon": "🤖"
        },
        {
            "id": "smartphone",
            "name": "Sampel Kamera HP (iPhone 15 Pro)",
            "description": "Jepretan smartphone dengan EXIF mobile & penajaman komputasi",
            "filename": "sample_smartphone.jpg",
            "icon": "📱"
        },
        {
            "id": "dslr",
            "name": "Sampel Kamera DSLR (Sony A7 IV)",
            "description": "Jepretan sensor Full-Frame dengan lensa optik 50mm f/1.8 & noise alami",
            "filename": "sample_dslr.jpg",
            "icon": "📷"
        },
        {
            "id": "webcam",
            "name": "Sampel Laptop / Webcam (Logitech C920)",
            "description": "Jepretan modul webcam 720p HD dengan lensa fixed & noise indoor",
            "filename": "sample_webcam.jpg",
            "icon": "💻"
        },
        {
            "id": "screenshot",
            "name": "Sampel Screenshot Layar (1080p Desktop UI)",
            "description": "Tangkapan layar resolusi 1920x1080 dengan elemen UI grafis & zero noise",
            "filename": "sample_screenshot.png",
            "icon": "🖥️"
        },
        {
            "id": "canva",
            "name": "Sampel Desain Canva (1080x1080 Post)",
            "description": "Desain poster template Canva dengan tipografi tajam, warna grafis sintetis & kanvas 1:1",
            "filename": "sample_canva.jpg",
            "icon": "🎨"
        }
    ]
    return samples

@app.get("/api/sample/{sample_id}")
async def analyze_sample(sample_id: str):
    """Jalankan analisis langsung pada salah satu sampel bawaan"""
    file_map = {
        "ai": "sample_ai.png",
        "smartphone": "sample_smartphone.jpg",
        "dslr": "sample_dslr.jpg",
        "webcam": "sample_webcam.jpg",
        "screenshot": "sample_screenshot.png",
        "canva": "sample_canva.jpg"
    }
    if sample_id not in file_map:
        raise HTTPException(status_code=404, detail="Sampel tidak ditemukan.")
        
    path = os.path.join(SAMPLES_DIR, file_map[sample_id])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Berkas sampel belum dibuat di disk.")
        
    with open(path, "rb") as f:
        data = f.read()
        
    return process_image_pipeline(data, filename=file_map[sample_id])

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Pita Detector", "version": "1.0.0"}

# Mount folder static untuk UI Web di root
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Memulai Pita Detector pada http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
