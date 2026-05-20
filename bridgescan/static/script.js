const overlayImage = document.getElementById("overlayImage");
const overlayPlaceholder = document.getElementById("overlayPlaceholder");
const API_URL = "/predict";
const imageUpload = document.getElementById("imageUpload");
const customUploadBtn = document.getElementById("customUploadBtn");
const preview = document.getElementById("preview");
const detectionResult = document.getElementById("detectionResult");
const confidenceBar = document.getElementById("confidenceBar");
const confidenceText = document.getElementById("confidenceText");
const severityBadge = document.getElementById("severityBadge");
const corrosionType = document.getElementById("corrosionType");
const actionText = document.getElementById("action");
// --- 2. Sidebar Collapse / Dropdown Logic ---
const submenuItems = document.querySelectorAll(".submenu-item");
submenuItems.forEach((item) => {
    item.addEventListener("click", () => {
        const parentLi = item.parentElement;
        document.querySelectorAll(".menu-content .item").forEach((li) => {
            if (li !== parentLi) li.classList.remove("show-submenu");
        });
        parentLi.classList.toggle("show-submenu");
    });
});

// --- 3. Sidebar Close Trigger ---
const sidebarClose = document.getElementById("sidebar-close");
const sidebar = document.querySelector(".sidebar");
const mainContent = document.querySelector(".main");
if (sidebarClose) {
    sidebarClose.addEventListener("click", () => {
        sidebar.classList.toggle("close");
        if (mainContent) mainContent.classList.toggle("fullscreen");
    });
}

// --- 4. Custom Upload Button Activator ---
if (customUploadBtn && imageUpload) {
    customUploadBtn.addEventListener("click", function (e) {
        e.preventDefault();
        imageUpload.click();
    });
}

// --- 5. Main Prediction and Engine Pipeline ---
if (imageUpload) {
    imageUpload.addEventListener("change", async function (e) {
        const file = e.target.files[0];
        if (!file) return;

        // Preview rendering
        if (preview) {
            preview.src = URL.createObjectURL(file);
            preview.style.display = "block";
            preview.style.width = '512px';
            preview.style.height = '512px';
            preview.style.objectFit = 'cover';
        }

        if (overlayImage) {
            overlayImage.style.display = "none";
        }

        if (overlayPlaceholder) {
            overlayPlaceholder.style.display = "flex";
        }

        // Loading States UI Update
        if (detectionResult) {
            detectionResult.innerText = "🔄 Initializing Segmentation Engine...";
            detectionResult.style.color = "#64748b";
        }
        if (confidenceText) confidenceText.innerText = "Processing...";
        if (confidenceBar) {
            confidenceBar.style.width = "25%";
            confidenceBar.style.backgroundColor = "#cbd5e1";
        }
        if (severityBadge) {
            severityBadge.innerText = "SCANNING";
            severityBadge.style.backgroundColor = "#94a3b8";
        }
        if (corrosionType) corrosionType.innerText = "Analyzing pixel segments...";
        if (actionText) actionText.innerText = "Calculating engine repair strategy...";

        // Form Data Preparation
        const formData = new FormData();
        formData.append("image", file);

        try {
            const response = await fetch(API_URL, { method: "POST", body: formData });
            if (!response.ok) throw new Error(`Server Error Code: ${response.status}`);
            const data = await response.json();

            // Result Rendering
            if (detectionResult) {
                detectionResult.innerText = data.prediction || "Complete";
                detectionResult.style.color = data.prediction === "ANOMALY DETECTED" ? "#ef4444" : "#22c55e";
            }

            // Confidence Bar Animation
            const score = data.confidence || 0;
            if (confidenceText) confidenceText.innerText = `${score}%`;
            if (confidenceBar) {
                confidenceBar.style.width = `${score}%`;
                if (score > 85) confidenceBar.style.backgroundColor = "#22c55e";
                else if (score > 65) confidenceBar.style.backgroundColor = "#eab308";
                else confidenceBar.style.backgroundColor = "#ef4444";
            }

            // Severity Badge Logic with Dynamic Color Mapping
            if (severityBadge) {
                const badgeState = data.severity ? data.severity.toUpperCase() : "GOOD";
                severityBadge.innerText = badgeState;
                const colors = {
                    "BAD": "#b91c1c",
                    "POOR": "#ea580c",
                    "FAIR": "#ca8a04",
                    "GOOD": "#22c55e"
                };
                severityBadge.style.backgroundColor = colors[badgeState] || "#94a3b8";
                severityBadge.style.color = "#ffffff";
            }

            // Extended Info
            if (corrosionType) corrosionType.innerText = `${data.defect_type || 'Unknown'} | Density: ${data.density || 0}%`;
            if (actionText) actionText.innerText = data.suggestion || "-";

            // SHOW SEGMENTATION OVERLAY
            if (data.overlay && overlayImage) {
                overlayImage.src = data.overlay;
                overlayImage.style.display = "block";
                if (overlayPlaceholder) {
                    overlayPlaceholder.style.display = "none";
                }
            }
        } catch (error) {
            console.error("Pipeline Exception Triggered:", error);
            if (detectionResult) {
                detectionResult.innerText = "❌ Engine Error Found";
                detectionResult.style.color = "#ef4444";
            }
            if (actionText) actionText.innerText = "Failed to communicate with Flask AI processing blocks.";
        }
    });
}
// --- 6. Helper Utility: System Logger ---
console.log("BridgeScan AI Engine initialized. Awaiting user input...");