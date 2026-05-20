import os
import torch
import numpy as np
import cv2
import base64
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F

from network._deeplab import DeepLabV3 #type: ignore

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

MODEL_PATH = "weights_final.pt"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = None
try:
    print(f"Loading model from {MODEL_PATH} on {DEVICE}...")
    torch.serialization.add_safe_globals([DeepLabV3])
    model = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)
    model.to(DEVICE)
    model.eval()
    print("✅ MODEL LOADED SUCCESSFULLY")
except Exception as e:
    print(f"❌ MODEL LOAD ERROR: {e}")

transform = T.Compose([
    T.Resize((512, 512)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files["image"]
    image = Image.open(file).convert("RGB")
    
   
    input_tensor = transform(image).unsqueeze(0).to(DEVICE)
    
    with torch.no_grad():
        output = model(input_tensor)
        if isinstance(output, dict):
            output = output["out"]
            
        mask = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()
        
        probs = F.softmax(output, dim=1)
        max_prob, _ = torch.max(probs, dim=1)
        confidence = int(max_prob.mean().item() * 100)

    counts = [np.sum(mask == i) for i in range(4)]
    total_pixels = mask.size

    threshold = 100 

    if counts[3] > threshold:
        idx = 3
    elif counts[2] > threshold:
        idx = 2
    elif counts[1] > threshold:
        idx = 1
    else:
        idx = 0
    
    labels = {0: "Good", 1: "Fair", 2: "Poor", 3: "Severe"}
    suggestions = {
        0: "Routine inspection only.",
        1: "Cleaning and minor repaint recommended.",
        2: "Abrasive blast and anti-corrosion coating required.",
        3: "Structural intervention and repair urgent."
    }

    overlay = np.zeros((512, 512, 3), dtype=np.uint8)
    colors = {1: [0, 165, 255], 2: [0, 255, 255], 3: [0, 0, 255]} 
    for i in range(1, 4):
        overlay[mask == i] = colors[i]
        
    blended = cv2.addWeighted(np.array(image.resize((512, 512))), 0.6, overlay, 0.4, 0)
    _, buffer = cv2.imencode('.png', cv2.cvtColor(blended, cv2.COLOR_RGB2BGR))
    overlay_data = "data:image/png;base64," + base64.b64encode(buffer).decode("utf-8")
    
    return jsonify({
        "prediction": "ANOMALY DETECTED" if idx > 0 else "HEALTHY STRUCTURE",
        "defect_type": labels[idx],
        "severity": labels[idx],
        "suggestion": suggestions[idx],
        "density": round(((sum(counts[1:]) / total_pixels) * 100), 2),
        "confidence": confidence,
        "overlay": overlay_data
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)