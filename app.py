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

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit


def run_demucs(file_path, job_id):
    command = [
        "demucs",
        "--two-stems=vocals",
        "--device", "cpu",
        "-o", OUTPUT_FOLDER,
        file_path
    ]
    subprocess.run(command)


@app.route("/api/separate", methods=["POST"])
def separate_audio():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    job_id = str(uuid.uuid4())

    filename = f"{job_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    try:
        run_demucs(file_path, job_id)

        # Demucs output folder path
        folder_name = os.listdir(OUTPUT_FOLDER)[0]
        stem_path = os.path.join(OUTPUT_FOLDER, folder_name)

        stems = {}
        for stem_file in os.listdir(stem_path):
            stems[stem_file.split(".")[0]] = f"/download/{folder_name}/{stem_file}"

        return jsonify({
            "jobId": job_id,
            "name": file.filename.rsplit(".", 1)[0],
            "stems": stems,
            "status": "completed"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download/<folder>/<filename>")
def download_file(folder, filename):
    return send_from_directory(
        os.path.join(OUTPUT_FOLDER, folder),
        filename,
        as_attachment=True
    )


@app.route("/")
def home():
    return "Lions Flute Backend Running 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
