import os
import sys
import torch
import numpy as np
import cv2
import base64
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from PIL import Image
import torchvision.transforms as T

# Import your network architecture
sys.path.append("./network")
from network._deeplab import DeepLabV3

# ============================================================
# CONFIGURATION
# ============================================================
MODEL_PATH = "weights_12.pt"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# IMPORTANTE: Ito ang mean/std na ginamit sa training mo (Standard ImageNet)
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
logging.basicConfig(level=logging.INFO)

# ============================================================
# MODEL LOADING
# ============================================================
try:
    print(f"Loading model from {MODEL_PATH} on {DEVICE}...")
    # Load as full model object as per your file structure
    model = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)
    model.to(DEVICE)
    model.eval()
    print("✅ MODEL LOADED SUCCESSFULLY")
except Exception as e:
    print(f"❌ MODEL LOAD ERROR: {e}")
    model = None

# ============================================================
# PRE-PROCESSING (Tugma sa Training)
# ============================================================
transform = T.Compose([
    T.Resize((512, 512)),
    T.ToTensor(),
    T.Normalize(mean=NORM_MEAN, std=NORM_STD) 
])

# ============================================================
# ROUTES
# ============================================================
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400
    
    file = request.files["image"]
    image = Image.open(file).convert("RGB")
    original_image = image.copy()
    
    # Preprocess
    input_tensor = transform(image).unsqueeze(0).to(DEVICE)
    
    with torch.no_grad():
        output = model(input_tensor)
        # DeepLabV3 usually returns a dict with 'out'
        if isinstance(output, dict):
            output = output["out"]
            
        mask = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()

        unique_vals, counts_per_class = np.unique(mask, return_counts=True)
        print(f"DEBUG: Unique values found: {unique_vals}")
        print(f"DEBUG: Counts per class: {counts_per_class}")

    # Analysis logic
    counts = [np.sum(mask == i) for i in range(4)]
    total_pixels = mask.size
    damage_pixels = sum(counts[1:])
    damage_counts = counts[1:]
    density = round((damage_pixels / total_pixels) * 100, 2)
    
    dominant_idx = np.argmax(damage_counts) + 1 
    max_damage_pixels = max(damage_counts)
    
    print(f"\nDOMINANT DAMAGE CLASS: {dominant_idx}")
    print(f"MAX DAMAGE PIXELS: {max_damage_pixels}")
    
    if max_damage_pixels < 500: 
            idx = 0
            print("\nDecision: HEALTHY (Damage too low)")
    else:
            idx = dominant_idx
            print(f"\nDecision: ANOMALY DETECTED (Class {idx})")

    # Response details
    labels = {0: "Good", 1: "Fair", 2: "Poor", 3: "Severe"}
    suggestions = {
        0: "Routine inspection.",
        1: "Abrasive blast and repaint.",
        2: "Apply anti-corrosion coating.",
        3: "Structural strengthening required."
    }
    
    # Overlay creation
    overlay = np.zeros_like(np.array(original_image.resize((512, 512))), dtype=np.uint8)
    colors = {1: [255, 165, 0], 2: [255, 255, 0], 3: [255, 0, 0]}
    for i in range(1, 4):
        overlay[mask == i] = colors[i]
        
    blended = cv2.addWeighted(np.array(original_image.resize((512, 512))), 0.6, overlay, 0.4, 0)
    _, buffer = cv2.imencode('.png', cv2.cvtColor(blended, cv2.COLOR_RGB2BGR))
    overlay_data = "data:image/png;base64," + base64.b64encode(buffer).decode("utf-8")
    
    return jsonify({
        "prediction": "Anomaly Detected" if idx > 0 else "Healthy Structure",
        "defect_type": f"State {idx} - {labels[idx]}",
        "severity": labels[idx],
        "suggestion": suggestions[idx],
        "density": density,
        "confidence": min(95, 70 + int(density * 2)),
        "overlay": overlay_data
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)