import os
import torch
import numpy as np
import cv2
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F

from model_plus import createDeepLabv3Plus

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

WEIGHTS_PATH = "weights_final.pt"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Initializing model on {DEVICE}...")
model = createDeepLabv3Plus(outputchannels=4, output_stride=8)
model.to(DEVICE)

try:
    state_dict = torch.load(WEIGHTS_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.eval()
    print("✅ MODEL LOADED SUCCESSFULLY")
except Exception as e:
    print(f"❌ MODEL LOAD ERROR: {e}")

transform = T.Compose([
    T.Resize((512, 512)),
    T.ToTensor()
])

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400

    file = request.files["image"]
    image_pil = Image.open(file).convert("RGB")

    input_tensor = transform(image_pil).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = model(input_tensor)
        preds = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()
        probs = F.softmax(output, dim=1)
        confidence = int(torch.max(probs, dim=1)[0].mean().item() * 100)

    total_pixels = 512 * 512
    counts = {
        "fair": int(np.sum(preds == 1)),
        "poor": int(np.sum(preds == 2)),
        "bad":  int(np.sum(preds == 3))
    }
    densities = {k: round((v / total_pixels) * 100, 2) for k, v in counts.items()}
    total_corrosion = counts["fair"] + counts["poor"] + counts["bad"]
    total_density   = round((total_corrosion / total_pixels) * 100, 2)

    idx = 0
    if counts["bad"]  > 100: idx = 3
    elif counts["poor"] > 100: idx = 2
    elif counts["fair"] > 100: idx = 1

    labels      = {0: "Healthy", 1: "Fair", 2: "Poor", 3: "Severe"}
    suggestions = {
        0: "No significant corrosion detected. Continue routine inspection schedule.",
        1: "Surface cleaning recommended. Monitor for further deterioration.",
        2: "Apply anti-corrosion coating. Schedule maintenance within 3 months.",
        3: "Structural repair is urgent. Restrict load and consult engineer immediately."
    }
    defect_map  = {0: "None", 1: "Surface Rust (Fair)", 2: "Moderate Corrosion (Poor)", 3: "Severe Corrosion (Bad)"}

    colors = np.array([
        [0,   0,   0  ],   # Background
        [255, 255, 0  ],   # Fair   — Yellow
        [255, 165, 0  ],   # Poor   — Orange
        [255, 0,   0  ]    # Bad    — Red
    ], dtype=np.uint8)

    mask_rgb = colors[preds]
    image_resized = np.array(image_pil.resize((512, 512)))
    overlay_img = image_resized.copy()
    corrosion_mask = preds > 0

    overlay_img[corrosion_mask] = cv2.addWeighted(
        image_resized[corrosion_mask], 0.4,
        mask_rgb[corrosion_mask],      0.6, 0
    ).squeeze()

    _, buffer = cv2.imencode('.png', cv2.cvtColor(overlay_img, cv2.COLOR_RGB2BGR))
    overlay_data = "data:image/png;base64," + base64.b64encode(buffer).decode("utf-8")

    return jsonify({
        "prediction":     "ANOMALY DETECTED" if idx > 0 else "HEALTHY STRUCTURE",
        "severity":       labels[idx],
        "suggestion":     suggestions[idx],
        "confidence":     confidence,
        "defect_type":    defect_map[idx],
        "density":        total_density,
        "densities": {
            "fair":  densities["fair"],
            "poor":  densities["poor"],
            "bad":   densities["bad"],
            "total": total_density,
            "fair_px":  counts["fair"],
            "poor_px":  counts["poor"],
            "bad_px":   counts["bad"],
        },
        "overlay": overlay_data
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
