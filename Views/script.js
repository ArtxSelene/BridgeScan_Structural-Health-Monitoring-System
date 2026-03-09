document.getElementById("themeToggle").onclick = () => {
    const dark = document.body.classList.toggle("dark");
    if (overviewMap) switchMapTiles(overviewMap, dark);
    if (searchMap) switchMapTiles(searchMap, dark);
};

function switchMapTiles(map, dark) {
    map.eachLayer(layer => {
        if (layer instanceof L.TileLayer) map.removeLayer(layer);
    });

    const url = dark
        ? "https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
        : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

    L.tileLayer(url, { attribution: "© OpenStreetMap" }).addTo(map);
}

function closeAllMaps() {
    overviewMapContainer.classList.add("hidden");
    searchMapContainer.classList.add("hidden");
    bridgeDetail.classList.add("hidden");
}

document.querySelectorAll('.menu-title').forEach(title => {
    title.addEventListener('click', () => {
        const parent = title.parentElement;
        document.querySelectorAll('.menu-item').forEach(item => {
            if (item !== parent) item.classList.remove('active');
        });
        parent.classList.toggle('active');
        closeAllMaps();
    });
});

const bridges = [
    { id: "MN001", name: "Alabang Bridge", location: "Muntinlupa", type: "Steel", age: 18, health: 92, damage: "None", lat: 14.416, lng: 121.043, history: ["2024 corrosion", "2025 repaint", "2026 inspection"] },
    { id: "MN002", name: "Tunasan Bridge", location: "Muntinlupa", type: "Steel", age: 24, health: 73, damage: "Corrosion", lat: 14.381, lng: 121.045, history: ["2023 rust", "2024 reinforcement"] },
    { id: "CE001", name: "Cebu Bridge 1", location: "Cebu", type: "Steel", age: 30, health: 70, damage: "Corrosion", lat: 10.3157, lng: 123.8854, history: ["2020 rust", "2022 repair"] },
    { id: "DA001", name: "Davao Steel Bridge", location: "Davao", type: "Steel", age: 25, health: 78, damage: "Cracks", lat: 7.1907, lng: 125.4553, history: ["2020 cracks", "2025 monitoring"] }
];

const bridgeMapBtn = document.getElementById("bridgeMapBtn");
const overviewMapContainer = document.getElementById("overviewMapContainer");
const searchMapContainer = document.getElementById("searchMapContainer");
const bridgeDetail = document.getElementById("bridgeDetail");
const searchInput = document.getElementById("searchInput");
const suggestionList = document.getElementById("suggestionList");
const closeSearchMap = document.getElementById("closeSearchMap");

let overviewMap;
let searchMap;

function markerColor(health) {
    if (health >= 85) return "green";
    if (health >= 70) return "orange";
    return "red";
}

function createMarker(lat, lng, color) {
    return L.circleMarker([lat, lng], {
        radius: 8,
        color: color,
        fillColor: color,
        fillOpacity: 0.9
    });
}

bridgeMapBtn.onclick = () => {
    overviewMapContainer.classList.remove("hidden");
    searchMapContainer.classList.add("hidden");
    bridgeDetail.classList.add("hidden");

    if (!overviewMap) {
        overviewMap = L.map("overviewMap").setView([12.8797, 121.7740], 6);
        switchMapTiles(overviewMap, document.body.classList.contains("dark"));

        bridges.forEach(b => {
            const marker = createMarker(b.lat, b.lng, markerColor(b.health)).addTo(overviewMap);
            marker.on("click", () => showDetails(b));
        });
    }

    setTimeout(() => overviewMap.invalidateSize(), 200);
};

function showDetails(b) {
    bridgeDetail.classList.remove("hidden");
    document.getElementById("bridgeName").innerText = b.name;
    document.getElementById("bridgeID").innerText = b.id;
    document.getElementById("bridgeLocation").innerText = b.location;
    document.getElementById("bridgeType").innerText = b.type;
    document.getElementById("bridgeAge").innerText = b.age + " years";
    document.getElementById("bridgeHealth").innerText = b.health;
    document.getElementById("bridgeDamage").innerText = b.damage;

    const history = document.getElementById("historyList");
    history.innerHTML = "";
    b.history.forEach(h => {
        const li = document.createElement("li");
        li.textContent = h;
        history.appendChild(li);
    });
}

searchInput.addEventListener("input", () => {
    const value = searchInput.value.toLowerCase();
    suggestionList.innerHTML = "";
    if (value === "") {
        suggestionList.classList.add("hidden");
        return;
    }

    const filtered = bridges.filter(b => b.name.toLowerCase().includes(value));
    filtered.forEach(b => {
        const li = document.createElement("li");
        li.textContent = b.name;
        li.onclick = () => {
            searchInput.value = b.name;
            suggestionList.classList.add("hidden");
            openSearchMap(b);
        };
        suggestionList.appendChild(li);
    });

    if (filtered.length > 0) suggestionList.classList.remove("hidden");
});

function openSearchMap(b) {
    searchMapContainer.classList.remove("hidden");
    overviewMapContainer.classList.add("hidden");
    showDetails(b);

    if (!searchMap) {
        searchMap = L.map("searchMap").setView([b.lat, b.lng], 13);
        switchMapTiles(searchMap, document.body.classList.contains("dark"));
    }

    searchMap.eachLayer(l => {
        if (l instanceof L.Marker || l instanceof L.CircleMarker) searchMap.removeLayer(l);
    });

    createMarker(b.lat, b.lng, markerColor(b.health)).addTo(searchMap);
    searchMap.flyTo([b.lat, b.lng], 13);
    setTimeout(() => searchMap.invalidateSize(), 200);
}

closeSearchMap.onclick = () => {
    searchMapContainer.classList.add("hidden");
    bridgeDetail.classList.add("hidden");
};