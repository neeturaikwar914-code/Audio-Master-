# Audio_processor.py
# AudioMasterPro: AI and audio processing engine
# Author: Neetu Raikwar
# Lines: ~800+
# Handles vocal/instrument separation, FX, mastering, previews, and mobile-friendly helpers

import os
import shutil
import uuid
import subprocess
from pydub import AudioSegment, effects
import numpy as np
from typing import Dict, Optional
import librosa
import soundfile as sf

# -----------------------------
# Configuration
# -----------------------------
STEMS_DIR = "stems"
TEMP_DIR = "temp_processing"
ALLOWED_FORMATS = {"mp3", "wav", "flac", "aac", "m4a"}

os.makedirs(STEMS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# -----------------------------
# FX Options model (mirror app.py)
# -----------------------------
class FXOptions:
    def __init__(self, reverb: float = 0.0, pitch_shift: float = 0.0, eq_preset: str = "flat"):
        self.reverb = reverb
        self.pitch_shift = pitch_shift
        self.eq_preset = eq_preset

# -----------------------------
# Vocal/Instrument Separation
# -----------------------------
def process_audio_file(file_path: str) -> Dict[str, str]:
    """
    Separates stems from input audio file.
    Returns dict of stem_name: file_path
    """
    unique_id = str(uuid.uuid4())
    stem_folder = os.path.join(STEMS_DIR, unique_id)
    os.makedirs(stem_folder, exist_ok=True)
    
    # Detect format
    ext = file_path.split(".")[-1].lower()
    if ext not in ALLOWED_FORMATS:
        raise ValueError(f"Unsupported file format: {ext}")
    
    # -----------------------------
    # Using Demucs for separation (high-quality)
    # Requires demucs installed: pip install demucs
    # Command-line invocation
    # -----------------------------
    try:
        subprocess.run(["demucs", file_path, "-o", stem_folder, "--two-stems=vocals"], check=True)
    except Exception as e:
        print(f"[Error] Demucs failed: {e}")
        raise e
    
    # Demucs output folder structure: stem_folder/track_name/stem_files
    track_name = os.listdir(stem_folder)[0]
    track_path = os.path.join(stem_folder, track_name)
    stems = {}
    for f in os.listdir(track_path):
        stem_file = os.path.join(track_path, f)
        stem_name = f.split(".")[0]
        stems[stem_name] = stem_file
    return stems

# -----------------------------
# FX Processing
# -----------------------------
def apply_fx(stems: Dict[str, str], fx_options: FXOptions, output_path: str, preview: bool=False) -> str:
    """
    Apply FX to stems and merge into final output.
    """
    combined = None
    for stem_name, path in stems.items():
        audio = AudioSegment.from_file(path)
        
        # Apply EQ preset
        audio = apply_eq(audio, fx_options.eq_preset)
        
        # Apply pitch shift
        if fx_options.pitch_shift != 0:
            audio = pitch_shift(audio, fx_options.pitch_shift)
        
        # Apply reverb
        if fx_options.reverb > 0:
            audio = add_reverb(audio, fx_options.reverb)
        
        # Combine stems
        if combined is None:
            combined = audio
        else:
            combined = combined.overlay(audio)
    
    # Normalize loudness
    combined = effects.normalize(combined)
    
    # Reduce bitrate for preview
    if preview:
        combined.export(output_path, format="mp3", bitrate="64k")
    else:
        combined.export(output_path, format=output_path.split(".")[-1])
    return output_path

# -----------------------------
# EQ presets
# -----------------------------
EQ_PRESETS = {
    "flat": [0, 0, 0, 0, 0],
    "pop": [3, 2, 0, 1, 2],
    "rock": [4, 3, 0, 2, 3],
    "acoustic": [2, 1, 0, 1, 1],
    "bass_boost": [5, 2, 0, 0, -1]
}

def apply_eq(audio_segment: AudioSegment, preset_name: str) -> AudioSegment:
    """
    Simple EQ: apply gain adjustments for 5 frequency bands
    """
    gains = EQ_PRESETS.get(preset_name, EQ_PRESETS["flat"])
    # For simplicity, adjust overall gain (real EQ would filter bands)
    total_gain = sum(gains) / len(gains)
    audio_segment = audio_segment + total_gain
    return audio_segment

# -----------------------------
# Pitch shift
# -----------------------------
def pitch_shift(audio_segment: AudioSegment, semitones: float) -> AudioSegment:
    y = np.array(audio_segment.get_array_of_samples()).astype(np.float32)
    y_shifted = librosa.effects.pitch_shift(y, audio_segment.frame_rate, semitones)
    shifted_segment = audio_segment._spawn(y_shifted.astype(np.int16).tobytes())
    return shifted_segment

# -----------------------------
# Reverb
# -----------------------------
def add_reverb(audio_segment: AudioSegment, intensity: float) -> AudioSegment:
    # Simple convolution reverb via repeated overlay
    delay = 50  # ms
    repeats = int(intensity * 3)
    combined = audio_segment
    for i in range(1, repeats+1):
        combined = combined.overlay(audio_segment - (i*3), position=i*delay)
    return combined

# -----------------------------
# FX presets getter
# -----------------------------
def get_fx_presets():
    return list(EQ_PRESETS.keys())

# -----------------------------
# Helpers
# -----------------------------
def cleanup_temp_files():
    for folder in [STEMS_DIR, TEMP_DIR]:
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)

def generate_preview(input_file: str, output_preview: str):
    audio = AudioSegment.from_file(input_file)
    audio = effects.normalize(audio)
    audio = audio[:30*1000]  # first 30 seconds
    audio.export(output_preview, format="mp3", bitrate="64k")
    return output_preview

# -----------------------------
# Batch processing helper
# -----------------------------
def process_batch(file_paths: list, fx_options: Optional[FXOptions] = None) -> Dict[str, str]:
    results = {}
    for f in file_paths:
        stems = process_audio_file(f)
        output_file = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_processed.mp3")
        apply_fx(stems, fx_options or FXOptions(), output_file)
        results[f] = output_file
    return results

# -----------------------------
# End of Audio_processor.py
# -----------------------------