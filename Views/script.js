const bridges = [
    { 
        name: "Metro Manila Skyway", 
        lat: 14.4906, lng: 121.0440, health: 88,
        details: `<p>Location: Metro Manila, Philippines</p><br><p>Starts: Magallanes, Makati City</p><p>Ends: Alabang, Muntinlupa City</p><p>Passes through: Makati, Taguig, Parañaque, Las Piñas, Muntinlupa</p><p>Age: 1995 (31 years old)</p><p>Health Status: Good</p><br><p>Damage: - None Detected</p><br><p>Last Scan: 2026-02-20</p>`
    },
    { 
        name: "San Juanico Bridge", 
        lat: 11.2986, lng: 124.9669, health: 82,
        details: `<p>Location: Leyte and Samar, Philippines</p><br><p>Starts: Tacloban City, Leyte</p><p>Ends: Santa Rita, Samar</p><p>Passes through: San Juanico Strait</p><p>Age: 1973 (53 years old)</p><p>Health Status: Fair to Good</p><br><p>Damage: - Minor Corrosion on Truss Section</p><br><p>Last Scan: 2026-01-15</p>`
    }
];

let overviewMap, searchMap;

const mouse = document.querySelector('.custom-mouse');
document.addEventListener('mousemove', (e) => {
    mouse.style.left = e.clientX + 'px';
    mouse.style.top = e.clientY + 'px';
});

const bridgeMapBtn = document.getElementById("bridgeMapBtn");
const otherFeatures = document.querySelectorAll(".other-feature");
const overviewMapContainer = document.getElementById("overviewMapContainer");
const searchMapContainer = document.getElementById("searchMapContainer");
const placeholderContent = document.getElementById("placeholderContent");
const bridgeDetail = document.getElementById("bridgeDetail");
const themeToggle = document.getElementById("themeToggle");
const searchInput = document.getElementById("searchInput");
const topSearchBar = document.getElementById("topSearchBar");
const suggestionList = document.getElementById("suggestionList");
const exitBtn = document.querySelector(".exit-map-btn");
const legend = document.getElementById("legend");
const featureTitle = document.getElementById("featureTitle");

function hideAllScreens() {
    overviewMapContainer.classList.add("hidden");
    searchMapContainer.classList.add("hidden");
    placeholderContent.classList.add("hidden");
    bridgeDetail.classList.add("hidden");
    suggestionList.classList.add("hidden");
    legend.classList.add("hidden");
    exitBtn.classList.add("hidden");
    document.body.classList.remove("map-active"); 
}

// Function to reset all menu items to collapsed state
function closeAllMenus() {
    document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('active'));
}

function updateDetailsPanel(bridge) {
    bridgeDetail.classList.remove("hidden");
    document.getElementById("bridgeName").innerText = bridge.name;
    document.getElementById("detailsContent").innerHTML = bridge.details;
}

// Category Toggle Logic
document.querySelectorAll('.menu-title').forEach(title => {
    title.addEventListener('click', () => {
        const parent = title.parentElement;
        const wasActive = parent.classList.contains('active');
        closeAllMenus();
        if (!wasActive) parent.classList.add('active');
    });
});

exitBtn.onclick = () => {
    hideAllScreens();
    topSearchBar.classList.remove("hidden"); 
};

// Selection Logic: These close the sidebar menu after selection
bridgeMapBtn.onclick = (e) => {
    e.preventDefault();
    hideAllScreens();
    closeAllMenus(); // Close sidebar on selection
    document.body.classList.add("map-active");
    topSearchBar.classList.remove("hidden");
    overviewMapContainer.classList.remove("hidden");
    legend.classList.remove("hidden");
    exitBtn.classList.remove("hidden");
    if (!overviewMap) {
        overviewMap = L.map("overviewMap", { zoomControl: false }).setView([12.8797, 121.7740], 6);
        L.control.zoom({ position: 'bottomleft' }).addTo(overviewMap);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(overviewMap);
        bridges.forEach(b => {
            L.marker([b.lat, b.lng], { icon: createTeardrop(b.health) }).addTo(overviewMap).on("click", () => updateDetailsPanel(b));
        });
    }
    setTimeout(() => overviewMap.invalidateSize(), 300);
};

searchInput.oninput = () => {
    const val = searchInput.value.toLowerCase();
    suggestionList.innerHTML = "";
    if(!val) { suggestionList.classList.add("hidden"); return; }
    const filtered = bridges.filter(b => b.name.toLowerCase().includes(val));
    filtered.forEach(b => {
        const li = document.createElement("li");
        li.innerText = b.name;
        li.onclick = () => {
            hideAllScreens();
            closeAllMenus(); // Close sidebar on selection
            document.body.classList.add("map-active");
            searchMapContainer.classList.remove("hidden");
            exitBtn.classList.remove("hidden");
            updateDetailsPanel(b); 
            if(!searchMap) {
                searchMap = L.map("searchMap", { zoomControl: false }).setView([b.lat, b.lng], 13);
                L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(searchMap);
            }
            searchMap.eachLayer(l => { if(l instanceof L.Marker) searchMap.removeLayer(l); });
            L.marker([b.lat, b.lng], { icon: createTeardrop(b.health) }).addTo(searchMap);
            searchMap.flyTo([b.lat, b.lng], 13);
            suggestionList.classList.add("hidden");
            searchInput.value = b.name;
        };
        suggestionList.appendChild(li);
    });
    suggestionList.classList.toggle("hidden", filtered.length === 0);
};

// Feature click logic: Closes the sidebar menu automatically
otherFeatures.forEach(btn => {
    btn.onclick = (e) => {
        e.preventDefault();
        hideAllScreens();
        closeAllMenus(); // Close sidebar on selection
        topSearchBar.classList.add("hidden"); 
        placeholderContent.classList.remove("hidden");
        featureTitle.innerText = e.currentTarget.innerText;
    };
});

themeToggle.onclick = () => {
    const isDark = document.body.classList.toggle("dark");
    themeToggle.querySelector("i").classList.toggle("fa-moon", !isDark);
    themeToggle.querySelector("i").classList.toggle("fa-sun", isDark);
};

function createTeardrop(health) {
    const color = health >= 85 ? "#2ecc71" : (health >= 70 ? "#f1c40f" : "#e74c3c");
    return L.divIcon({ className: 'custom-pin', html: `<i class="fa-solid fa-location-dot" style="color: ${color}; font-size:30px;"></i>`, iconSize: [30, 30], iconAnchor: [15, 30] });
}