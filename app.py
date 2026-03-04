from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import subprocess

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "separated"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024


def run_demucs(file_path):
    command = [
        "demucs",
        "--two-stems=vocals",
        "--device", "cpu",
        "-o", OUTPUT_FOLDER,
        file_path
    ]
    subprocess.run(command)


@app.route("/api/separate", methods=["POST"])
def separate():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    job_id = str(uuid.uuid4())

    filename = job_id + "_" + file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(file_path)

    try:

        run_demucs(file_path)

        model_folder = os.listdir(OUTPUT_FOLDER)[0]

        model_path = os.path.join(OUTPUT_FOLDER, model_folder)

        song_folder = os.listdir(model_path)[0]

        stem_path = os.path.join(model_path, song_folder)

        stems = {}

        for stem in os.listdir(stem_path):
            stems[stem.split(".")[0]] = f"/download/{model_folder}/{song_folder}/{stem}"

        return jsonify({
            "name": file.filename,
            "stems": stems,
            "status": "done"
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
    return "Audio Master Backend Running 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
