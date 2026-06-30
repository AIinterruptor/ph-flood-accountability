/* global L, Chart */

const STATUS_COLORS = {
  completed: '#22c55e',
  ongoing: '#3b82f6',
  suspended: '#f59e0b',
  under_investigation: '#6366f1',
  convicted: '#ef4444',
  charged: '#f97316',
  pending: '#eab308',
  acquitted: '#10b981',
};

let mapInstance = null;

function initMap(projects) {
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }

  mapInstance = L.map('map').setView([12.8797, 121.774], 6);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(mapInstance);

  projects.forEach(p => {
    if (!p.coordinates || p.coordinates.length < 2) return;
    const [lat, lng] = p.coordinates;
    const color = STATUS_COLORS[p.status] || '#6b7280';
    const marker = L.circleMarker([lat, lng], {
      radius: 8,
      fillColor: color,
      color: '#fff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85,
    }).addTo(mapInstance);
    marker.bindPopup(`
      <strong>${p.name}</strong><br>
      ${p.agency} · ${p.region}<br>
      Status: ${p.status.replace('_', ' ')}<br>
      Budget: ₱${p.budget_php.toLocaleString()}<br>
      Cases: ${p.cases.length} | Persons: ${p.persons.length}
    `);
  });
}

window.initMap = initMap;
