from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from PIL import Image
from ultralytics import YOLO


PORT = 5000
HOST = '0.0.0.0'

app = Flask(__name__)
CORS(app)

IMG_SIZE = (512, 512)

model = YOLO('best.pt')

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return "BridgeScan API Running"


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({
            "error": "No image uploaded"
        }), 400

    file = request.files["image"]

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only JPG, JPEG, and PNG are allowed."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    img = Image.open(filepath)
    img = img.resize(IMG_SIZE)
    img.save(filepath)

    results = model(filepath)[0]
    
    if results.boxes is not None and len(results.boxes) > 0:
        top_box = results.boxes[0]
        conf = int(top_box.conf[0] * 100)
        label = results.names[int(top_box.cls[0])]
        
        if results.masks is not None:
            prediction = f"{label} Segmented (Masking Applied)"
        else:
            prediction = f"{label} Detected (Bounding Box)"
            
        severity = "Bad" if conf > 80 else "Poor" if conf > 50 else "Fair"
        suggestion = "Immediate engineering assessment required." if conf > 80 else "Schedule maintenance soon."
    else:
        prediction = "No Damage Detected"
        conf = 0
        label = "Healthy"
        severity = "Good"
        suggestion = "No immediate action required."

    result = {
        "prediction": prediction,
        "confidence": conf,
        "severity": severity,
        "corrosion_type": label,
        "suggestion": suggestion
    }

    return jsonify(result)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)