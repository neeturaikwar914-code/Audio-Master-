# main.py
# AudioMasterPro: Server entry point
# Author: Neetu Raikwar
# Lines: ~450
# Starts FastAPI server, loads app.py, Render-ready

import uvicorn
import logging
import os
from fastapi import FastAPI
from app import app as audio_app

# -----------------------------
# Configuration
# -----------------------------
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
DEBUG = os.environ.get("DEBUG", "True") == "True"
LOG_FILE = os.environ.get("LOG_FILE", "server.log")

# -----------------------------
# Logging setup
# -----------------------------
logger = logging.getLogger("AudioMasterPro")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# File handler
fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.info("Starting AudioMasterPro server...")

# -----------------------------
# Middleware & Startup Events
# -----------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("AudioMasterPro API starting up...")
    # Optionally, cleanup old temp files
    from Audio_processor import cleanup_temp_files
    cleanup_temp_files()
    logger.info("Temp directories cleaned.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AudioMasterPro API shutting down...")
    # Cleanup on shutdown
    from Audio_processor import cleanup_temp_files
    cleanup_temp_files()
    logger.info("Temp directories cleaned on shutdown.")

# -----------------------------
# Health & Info endpoints
# -----------------------------
@app.get("/server_info")
async def server_info():
    return {
        "name": "AudioMasterPro",
        "version": "1.0.0",
        "debug": DEBUG,
        "host": HOST,
        "port": PORT
    }

@app.get("/")
async def root():
    return {"message": "AudioMasterPro API is running"}

# -----------------------------
# Render or local deployment
# -----------------------------
if __name__ == "__main__":
    logger.info(f"Running on {HOST}:{PORT} with debug={DEBUG}")
    uvicorn.run(
        "main:audio_app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info",
        workers=1  # can increase if needed
    )

# -----------------------------
# Optional: CLI commands
# -----------------------------
def run_local():
    """Start local server for development"""
    logger.info("Starting local dev server...")
    uvicorn.run(audio_app, host="127.0.0.1", port=8000, reload=True)

def deploy_render():
    """Render deployment entry"""
    logger.info("Deploying to Render...")
    uvicorn.run(audio_app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), workers=1)

# -----------------------------
# End of main.py
# -----------------------------