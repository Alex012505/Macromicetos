import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Occurrence, Taxon } from '../types';
import { Notice } from './UI';

export default function OccurrenceMap({ records, taxa, onSelect, compact = false }: {
  records: Occurrence[]; taxa: Taxon[]; onSelect: (o: Occurrence) => void; compact?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const markers = useRef<L.LayerGroup | null>(null);
  const callback = useRef(onSelect);
  callback.current = onSelect;
  const [tileError, setTileError] = useState(false);
  useEffect(() => {
    if (!container.current) return;
    const instance = L.map(container.current, { scrollWheelZoom: !compact, zoomControl: !compact }).setView([5.15, -71.5], compact ? 5 : 6);
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 18,
    }).addTo(instance);
    tiles.on('tileerror', () => setTileError(true));
    markers.current = L.layerGroup().addTo(instance);
    map.current = instance;
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(container.current);
    return () => { observer.disconnect(); instance.remove(); map.current = null; markers.current = null; };
  }, [compact]);
  useEffect(() => {
    if (!map.current || !markers.current) return;
    markers.current.clearLayers();
    const coords: L.LatLngTuple[] = [];
    records.forEach(o => {
      if (o.lat == null || o.lng == null) return;
      const taxon = taxa.find(t => t.id === o.taxonId);
      const color = o.status === 'verified' ? '#226b53' : o.status === 'pending' ? '#bd7c24' : '#8d6b6a';
      const node = document.createElement('div');
      const title = document.createElement('strong'); title.textContent = taxon?.scientificName || 'Ocurrencia';
      const place = document.createElement('p'); place.textContent = o.locality;
      const button = document.createElement('button'); button.className = 'map-popup-button'; button.textContent = 'Ver ficha';
      button.addEventListener('click', () => callback.current(o)); node.append(title, place, button);
      L.circleMarker([o.lat, o.lng], { radius: compact ? 5 : 9, color: '#fff', weight: 2, fillColor: color, fillOpacity: 1 })
        .bindPopup(node).addTo(markers.current!);
      coords.push([o.lat, o.lng]);
    });
    if (coords.length) map.current.fitBounds(L.latLngBounds(coords), { padding: compact ? [25, 25] : [50, 50], maxZoom: compact ? 6 : 11 });
  }, [records, taxa, compact]);
  return <div className={`map-container ${compact ? 'compact' : ''}`}>
    <div className="leaflet-map" ref={container} aria-label="Mapa interactivo de ocurrencias de macromicetos" />
    {tileError && !compact && <div className="map-warning"><Notice>El fondo cartográfico no está disponible. Los marcadores siguen mostrando las coordenadas; revisa tu conexión a internet.</Notice></div>}
  </div>;
}
