const sidebar = document.querySelector(".sidebar");
const sidebarClose = document.querySelector("#sidebar-close");
const menu = document.querySelector(".menu-content");
const menuItems = document.querySelectorAll(".submenu-item");
const subMenuTitles = document.querySelectorAll(".submenu .menu-title");

const API_URL = "http://127.0.0.1:5000";

sidebarClose.addEventListener("click", () => {
  sidebar.classList.toggle("close");
});

const allLinks = document.querySelectorAll(".item a, .submenu-item, .submenu .menu-title");
allLinks.forEach(link => {
  link.addEventListener("click", function() {
    if (!this.classList.contains("submenu-item")) {
        document.querySelectorAll(".item").forEach(item => item.classList.remove("active"));
    }
    this.parentElement.classList.add("active");
  });
});

menuItems.forEach((item, index) => {
  item.addEventListener("click", () => {
    menu.classList.add("submenu-active");
    item.classList.add("show-submenu");

    menuItems.forEach((item2, index2) => {
      if (index !== index2) {
        item2.classList.remove("show-submenu");
      }
    });
  });
});

subMenuTitles.forEach((title) => {
  title.addEventListener("click", () => {
    menu.classList.remove("submenu-active");

    menuItems.forEach((item) => {
      item.classList.remove("show-submenu");
    });
  });
});

const camera = document.getElementById("camera");
const startBtn = document.getElementById("startCamera");
const stopBtn = document.getElementById("stopCamera");
const captureCanvas = document.getElementById("captureCanvas");
const statusDot = document.querySelector(".status-dot");
const cameraPlaceholder = document.getElementById("camera-placeholder");

let stream = null;
let liveAnalysisInterval = null;

startBtn.addEventListener("click", async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: true,
    });

    camera.srcObject = stream;
    statusDot.classList.add("active");
    statusDot.classList.remove("offline");
    cameraPlaceholder.classList.add("hidden-camera");
    camera.classList.remove("hidden-camera");
    statusDot.innerHTML = '<span class="pulse"></span> LIVE';
    startBtn.disabled = true;
    stopBtn.disabled = false;

    liveAnalysisInterval = setInterval(analyzeLiveFrame, 3000);

  } catch (err) {
    console.log("Camera error:", err);
    alert("Could not access camera. Please check permissions.");
  }
});

stopBtn.addEventListener("click", () => {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    clearInterval(liveAnalysisInterval);

    camera.srcObject = null;
    statusDot.classList.remove("active");
    statusDot.classList.add("offline");
    cameraPlaceholder.classList.remove("hidden-camera");
    camera.classList.add("hidden-camera");
    statusDot.innerHTML = "● OFFLINE";
    startBtn.disabled = false;
    stopBtn.disabled = true;

    resetDashboardUI();
  }
});

function resetDashboardUI() {
  document.getElementById("detectionResult").innerText = "No detection yet";
  document.getElementById("confidenceBar").style.width = "0%";
  document.getElementById("confidenceText").innerText = "0%";
  
  const severityBadge = document.getElementById("severityBadge");
  severityBadge.className = "severity-badge";
  severityBadge.innerText = "-";

  document.getElementById("corrosionType").innerText = "-";
  document.getElementById("action").innerText = "-";
}

async function analyzeLiveFrame() {
  if (!stream) return;

  const context = captureCanvas.getContext("2d");
  captureCanvas.width = camera.videoWidth;
  captureCanvas.height = camera.videoHeight;
  
  context.drawImage(camera, 0, 0, captureCanvas.width, captureCanvas.height);
  
  captureCanvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append("image", blob, "live-frame.jpg");

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        body: formData
      });
      const data = await response.json();
      updateDashboardUI(data);
    } catch (err) {
      console.error("Live analysis error:", err);
    }
  }, "image/jpeg", 0.8);
}

function updateDashboardUI(data) {
  const detectionResult = document.getElementById("detectionResult");
  const confidenceBar = document.getElementById("confidenceBar");
  const confidenceText = document.getElementById("confidenceText");
  const severityBadge = document.getElementById("severityBadge");
  const corrosionType = document.getElementById("corrosionType");
  const action = document.getElementById("action");

  detectionResult.innerText = data.prediction;
  corrosionType.innerText = data.corrosion_type;
  action.innerText = data.suggestion;
  
  const conf = data.confidence;
  confidenceBar.style.width = `${conf}%`;
  confidenceText.innerText = `${conf}% Confidence`;

  if (conf >= 80) {
    confidenceBar.style.background = "var(--success)";
  } else if (conf >= 50) {
    confidenceBar.style.background = "var(--warning)";
  } else {
    confidenceBar.style.background = "var(--danger)";
  }

  severityBadge.className = "severity-badge";
  const sev = data.severity.toLowerCase();
  if (sev === "good") {
    severityBadge.classList.add("good");
  } else if (sev === "fair") {
    severityBadge.classList.add("fair");
  } else if (sev === "poor") {
    severityBadge.classList.add("poor");
  } else {
    severityBadge.classList.add("bad");
  }
  severityBadge.innerText = data.severity.toUpperCase();
}

const imageUpload = document.getElementById("imageUpload");
const preview = document.getElementById("preview");

imageUpload.addEventListener("change", function () {

  const file = this.files[0];

  if (!file) return;

  preview.src = URL.createObjectURL(file);
  
  const resultText = document.getElementById("detectionResult");
  resultText.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
  
  const confidenceBar = document.getElementById("confidenceBar");
  confidenceBar.style.width = "0%";

  const formData = new FormData();
  formData.append("image", file);

  fetch(`${API_URL}/predict`, {
    method: "POST",
    body: formData
  })
  .then(res => res.json())
  .then(data => updateDashboardUI(data))
  .catch(err => {
    console.log("API Error:", err);
  });

});