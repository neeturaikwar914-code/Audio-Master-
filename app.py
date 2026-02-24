# app.py
# AudioMasterPro: FastAPI backend routes and mobile-ready API logic
# Author: Neetu Raikwar
# Lines: ~800+
# Note: Connects to Audio_processor.py for AI/audio processing

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import uuid
import asyncio
import time
from typing import List, Dict, Optional
from Audio_processor import process_audio_file, apply_fx, get_fx_presets

# -----------------------------
# App setup
# -----------------------------
app = FastAPI(title="AudioMasterPro API", version="1.0.0")

# CORS for mobile access
origins = ["*"]  # Adjust if needed for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Configuration
# -----------------------------
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
PREVIEW_DIR = "previews"
ALLOWED_EXTENSIONS = {"mp3", "wav", "flac", "aac", "m4a"}
MAX_FILE_SIZE_MB = 100  # mobile-friendly

# Create directories if not exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

# -----------------------------
# Helper functions
# -----------------------------
def check_file_extension(filename: str) -> bool:
    ext = filename.split(".")[-1].lower()
    return ext in ALLOWED_EXTENSIONS

def save_upload_file(upload_file: UploadFile, destination: str):
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()

def generate_unique_id() -> str:
    return str(uuid.uuid4())

async def run_in_background(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)

def get_file_size_mb(file_path: str) -> float:
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)

def cleanup_file(file_path: str):
    if os.path.exists(file_path):
        os.remove(file_path)

# -----------------------------
# Models
# -----------------------------
class FXOptions(BaseModel):
    reverb: Optional[float] = 0.0
    pitch_shift: Optional[float] = 0.0
    eq_preset: Optional[str] = "flat"

class ProcessRequest(BaseModel):
    upload_id: str
    fx_options: Optional[FXOptions] = FXOptions()
    export_format: Optional[str] = "mp3"

# -----------------------------
# In-memory status tracking
# -----------------------------
# Key = upload_id, value = status dict
processing_status: Dict[str, Dict] = {}

# -----------------------------
# Routes
# -----------------------------
@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    if not check_file_extension(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    upload_id = generate_unique_id()
    save_path = os.path.join(UPLOAD_DIR, f"{upload_id}_{file.filename}")
    save_upload_file(file, save_path)
    size_mb = get_file_size_mb(save_path)
    if size_mb > MAX_FILE_SIZE_MB:
        cleanup_file(save_path)
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit")
    # Initialize processing status
    processing_status[upload_id] = {"status": "uploaded", "progress": 0, "filename": file.filename}
    return {"upload_id": upload_id, "filename": file.filename, "status": "uploaded"}

@app.post("/process")
async def process_audio(request: ProcessRequest, background_tasks: BackgroundTasks):
    upload_id = request.upload_id
    if upload_id not in processing_status:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    orig_filename = processing_status[upload_id]["filename"]
    input_path = os.path.join(UPLOAD_DIR, f"{upload_id}_{orig_filename}")
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Uploaded file missing")
    output_filename = f"{upload_id}_processed.{request.export_format}"
    output_path = os.path.join(PROCESSED_DIR, output_filename)

    # Update status
    processing_status[upload_id]["status"] = "processing"
    processing_status[upload_id]["progress"] = 10

    # Run AI processing in background
    def background_process():
        # Step 1: Vocal/instrument separation
        stems = process_audio_file(input_path)
        processing_status[upload_id]["progress"] = 50
        # Step 2: Apply FX
        processed_file = apply_fx(stems, request.fx_options, output_path)
        processing_status[upload_id]["progress"] = 90
        # Step 3: Done
        processing_status[upload_id]["status"] = "done"
        processing_status[upload_id]["progress"] = 100
        return processed_file

    background_tasks.add_task(background_process)
    return {"upload_id": upload_id, "status": "processing"}

@app.get("/download/{upload_id}")
async def download_processed(upload_id: str):
    if upload_id not in processing_status or processing_status[upload_id]["status"] != "done":
        raise HTTPException(status_code=404, detail="File not ready")
    filename = processing_status[upload_id]["filename"]
    output_path = os.path.join(PROCESSED_DIR, f"{upload_id}_processed.mp3")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Processed file missing")
    return FileResponse(output_path, filename=f"{filename}_processed.mp3", media_type="audio/mpeg")

@app.get("/status/{upload_id}")
async def get_status(upload_id: str):
    if upload_id not in processing_status:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    return processing_status[upload_id]

@app.get("/preview/{upload_id}")
async def preview_audio(upload_id: str):
    preview_path = os.path.join(PREVIEW_DIR, f"{upload_id}_preview.mp3")
    if not os.path.exists(preview_path):
        # Generate preview if missing
        orig_filename = processing_status[upload_id]["filename"]
        input_path = os.path.join(UPLOAD_DIR, f"{upload_id}_{orig_filename}")
        apply_fx(input_path, FXOptions(), preview_path, preview=True)
    return FileResponse(preview_path, filename=f"{upload_id}_preview.mp3", media_type="audio/mpeg")

@app.get("/fx_options")
async def get_available_fx():
    presets = get_fx_presets()
    return {"presets": presets}

@app.post("/batch_process")
async def batch_process(files: List[UploadFile] = File(...), fx_options: FXOptions = FXOptions()):
    results = []
    for file in files:
        upload_resp = await upload_audio(file)
        req = ProcessRequest(upload_id=upload_resp["upload_id"], fx_options=fx_options)
        await process_audio(req, BackgroundTasks())
        results.append({"upload_id": upload_resp["upload_id"], "status": "processing"})
    return {"batch": results}

@app.post("/reset")
async def reset_all():
    # Cleanup all uploaded and processed files
    for folder in [UPLOAD_DIR, PROCESSED_DIR, PREVIEW_DIR]:
        for f in os.listdir(folder):
            cleanup_file(os.path.join(folder, f))
    processing_status.clear()
    return {"status": "reset_done"}

@app.get("/history")
async def get_history():
    history_list = [{"upload_id": uid, "status": info["status"], "filename": info["filename"]} for uid, info in processing_status.items()]
    return {"history": history_list}

# -----------------------------
# Extra mobile-friendly utilities
# -----------------------------
@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok", "uploads": len(processing_status)}

@app.get("/version")
async def version():
    return {"version": "1.0.0", "name": "AudioMasterPro API"}

# -----------------------------
# End of app.py
# -----------------------------