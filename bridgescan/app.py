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

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# CONFIGURATION
MODEL_PATH = "weights_final.pt" # Siguraduhing ito ang pangalan pagkatapos ng training
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# LOADING MODEL
try:
    print(f"Loading model from {MODEL_PATH}...")
    model = torch.load(MODEL_PATH, map_location=DEVICE)
    model.to(DEVICE)
    model.eval()
    print("✅ MODEL READY")
except Exception as e:
    print(f"❌ ERROR: {e}")
    model = None

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
    if "image" not in request.files: return jsonify({"error": "No image"}), 400
    
    file = request.files["image"]
    image = Image.open(file).convert("RGB")
    original_size = image.size
    
    input_tensor = transform(image).unsqueeze(0).to(DEVICE)
    
    with torch.no_grad():
        output = model(input_tensor)
        if isinstance(output, dict): output = output["out"]
        
        mask = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()
        probs = F.softmax(output, dim=1)
        max_prob, _ = torch.max(probs, dim=1)
        confidence = int(max_prob.mean().item() * 100)

    # ANALYSIS LOGIC
    counts = [np.sum(mask == i) for i in range(4)]
    density = round(((sum(counts[1:]) / mask.size) * 100), 2)
    idx = np.argmax(counts)
    
    # Threshold logic
    if idx == 0 and density < 2.0: 
        idx = 0 # Healthy
    
    labels = {0: "Good", 1: "Fair", 2: "Poor", 3: "Severe"}
    suggestions = {
        0: "Routine inspection only.",
        1: "Cleaning and minor repaint recommended.",
        2: "Abrasive blast and anti-corrosion coating required.",
        3: "Structural intervention and repair urgent."
    }
    
    # OVERLAY (Base64)
    overlay = np.zeros((512, 512, 3), dtype=np.uint8)
    colors = {1: [0, 165, 255], 2: [0, 255, 255], 3: [0, 0, 255]} # BGR format
    for i in range(1, 4): overlay[mask == i] = colors[i]
        
    blended = cv2.addWeighted(np.array(image.resize((512, 512))), 0.6, overlay, 0.4, 0)
    _, buffer = cv2.imencode('.png', cv2.cvtColor(blended, cv2.COLOR_RGB2BGR))
    overlay_data = "data:image/png;base64," + base64.b64encode(buffer).decode("utf-8")
    
    return jsonify({
        "prediction": "ANOMALY DETECTED" if idx > 0 else "HEALTHY STRUCTURE",
        "defect_type": labels[idx],
        "severity": labels[idx],
        "suggestion": suggestions[idx],
        "density": density,
        "confidence": confidence,
        "overlay": overlay_data
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)