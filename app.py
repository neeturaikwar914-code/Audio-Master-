from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import subprocess
import shutil

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "separated"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def run_demucs(file_path):

    command = [
        "demucs",
        "-n", "htdemucs",
        "--device", "cpu",
        "-o", OUTPUT_FOLDER,
        file_path
    ]

    subprocess.run(command)


@app.route("/api/separate", methods=["POST"])
def separate():

    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["file"]

    job_id = str(uuid.uuid4())

    filename = job_id + "_" + file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    file.save(filepath)

    try:

        run_demucs(filepath)

        model_folder = os.path.join(OUTPUT_FOLDER, "htdemucs")

        song_folder = os.listdir(model_folder)[-1]

        stem_path = os.path.join(model_folder, song_folder)

        stems = {}

        for stem in os.listdir(stem_path):

            name = stem.split(".")[0]

            stems[name] = f"/download/htdemucs/{song_folder}/{stem}"

        return jsonify({
            "name": file.filename,
            "stems": stems
        })

    except Exception as e:

        return jsonify({"error": str(e)}), 500


@app.route("/download/<model>/<folder>/<filename>")
def download(model, folder, filename):

    return send_from_directory(
        os.path.join(OUTPUT_FOLDER, model, folder),
        filename,
        as_attachment=True
    )


@app.route("/")
def home():
    return "Audio Backend Running 🚀"


if __name__ == "__main__":
   app.run(host="0.0.0.0", port=10000)
