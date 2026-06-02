import os
import io
import json
import torch
import numpy as np
import cv2
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F
from tensorflow.keras.models import load_model as load_keras_model

from model_plus import createDeepLabv3Plus

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# ── CNN (DeepLabV3+) ─────────────────────────────────────────────────────────
WEIGHTS_PATH = "weights_final.pt"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Initializing CNN on {DEVICE}...")
model = createDeepLabv3Plus(outputchannels=4, output_stride=8)
model.to(DEVICE)

try:
    state_dict = torch.load(WEIGHTS_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.eval()
    print("✅ CNN LOADED SUCCESSFULLY")
except Exception as e:
    print(f"❌ CNN LOAD ERROR: {e}")

transform = T.Compose([
    T.Resize((512, 512)),
    T.ToTensor()
])

# ── AUTOENCODER (grayscale CAE) ──────────────────────────────────────────────
try:
    autoencoder = load_keras_model('autoencoder_v5.keras')
    with open('threshold.json', 'r') as f:
        AE_THRESHOLD = json.load(f)['threshold']
    print(f"✅ AUTOENCODER LOADED | Threshold: {AE_THRESHOLD:.6f}")
except Exception as e:
    print(f"❌ AUTOENCODER LOAD ERROR: {e}")
    autoencoder = None
    AE_THRESHOLD = None


def run_autoencoder(pil_image):
    """
    Shared helper — takes a PIL image, returns (damage_detected str, mse float).
    Preprocessing matches detect_and_box_anomaly_grayscale() in Colab exactly:
      - convert to grayscale
      - resize to 64x64
      - normalize to [0,1]
      - predict with autoencoder
      - MSE between input and reconstruction
    """
    gray = pil_image.convert('L').resize((64, 64))
    img_arr = np.array(gray, dtype=np.float32) / 255.0
    img_arr = img_arr.reshape(1, 64, 64, 1)

    reconstructed = autoencoder.predict(img_arr, verbose=0)
    mse = float(np.mean(np.square(img_arr - reconstructed)))

    result = "Anomaly Detected" if mse > AE_THRESHOLD else "Healthy Structure"
    return result, mse


def run_cnn(pil_image):
    """
    Shared helper — takes a PIL image, returns full CNN result dict
    including overlay base64 string.
    """
    input_tensor = transform(pil_image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output     = model(input_tensor)
        preds      = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()
        probs      = F.softmax(output, dim=1)
        confidence = int(torch.max(probs, dim=1)[0].mean().item() * 100)

    total_pixels = 512 * 512
    counts = {
        "fair": int(np.sum(preds == 1)),
        "poor": int(np.sum(preds == 2)),
        "bad":  int(np.sum(preds == 3))
    }
    densities       = {k: round((v / total_pixels) * 100, 2) for k, v in counts.items()}
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
    defect_map = {
        0: "None",
        1: "Surface Rust (Fair)",
        2: "Moderate Corrosion (Poor)",
        3: "Severe Corrosion (Bad)"
    }

    colors = np.array([
        [0,   0,   0  ],
        [255, 255, 0  ],
        [255, 165, 0  ],
        [255, 0,   0  ]
    ], dtype=np.uint8)

    mask_rgb       = colors[preds]
    image_resized  = np.array(pil_image.resize((512, 512)))
    overlay_img    = image_resized.copy()
    corrosion_mask = preds > 0

    overlay_img[corrosion_mask] = cv2.addWeighted(
        image_resized[corrosion_mask], 0.4,
        mask_rgb[corrosion_mask],      0.6, 0
    ).squeeze()

    _, buffer = cv2.imencode('.png', cv2.cvtColor(overlay_img, cv2.COLOR_RGB2BGR))
    overlay_data = "data:image/png;base64," + base64.b64encode(buffer).decode("utf-8")

    return {
        "severity":    labels[idx],
        "suggestion":  suggestions[idx],
        "confidence":  confidence,
        "defect_type": defect_map[idx],
        "density":     total_density,
        "densities": {
            "fair":    densities["fair"],
            "poor":    densities["poor"],
            "bad":     densities["bad"],
            "total":   total_density,
            "fair_px": counts["fair"],
            "poor_px": counts["poor"],
            "bad_px":  counts["bad"],
        },
        "overlay": overlay_data
    }


# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    """CNN — called on image upload."""
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400
    pil_image = Image.open(request.files["image"]).convert("RGB")
    return jsonify(run_cnn(pil_image))


@app.route("/predict/autoencoder", methods=["POST"])
def predict_autoencoder():
    """Autoencoder — called on image upload."""
    if autoencoder is None:
        return jsonify({"error": "Autoencoder not loaded"}), 500
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400
    pil_image = Image.open(request.files["image"]).convert("RGB")
    result, mse = run_autoencoder(pil_image)
    return jsonify({"damage_detected": result, "reconstruction_error": round(mse, 6)})


@app.route("/predict/camera", methods=["POST"])
def predict_camera():
    """
    Combined endpoint for live camera frames.
    Accepts a base64-encoded JPEG frame sent from the browser,
    runs BOTH models, and returns combined results in one response.
    """
    if autoencoder is None:
        return jsonify({"error": "Autoencoder not loaded"}), 500

    data = request.get_json()
    if not data or "frame" not in data:
        return jsonify({"error": "No frame"}), 400

    # Decode base64 frame from browser
    try:
        header, encoded = data["frame"].split(",", 1)
        frame_bytes = base64.b64decode(encoded)
        pil_image   = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
    except Exception as e:
        return jsonify({"error": f"Frame decode failed: {e}"}), 400

    # Run both models
    ae_result, ae_mse = run_autoencoder(pil_image)
    cnn_result        = run_cnn(pil_image)

    return jsonify({
        # Autoencoder
        "damage_detected":      ae_result,
        "reconstruction_error": round(ae_mse, 6),
        # CNN
        **cnn_result
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
