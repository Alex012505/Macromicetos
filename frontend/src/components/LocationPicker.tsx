import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LocateFixed, MapPin } from 'lucide-react';
import { Notice } from './UI';
import { getDeviceLocation } from '../lib/device-location.mjs';

export interface LocationSelection { lat: string; lng: string; source: 'device' | 'map' | 'manual'; uncertaintyM?: string; elevationM?: string }
export default function LocationPicker({ lat, lng, onChange, active = true }: { lat: string; lng: string; onChange: (v: LocationSelection) => void; active?: boolean }) {
  const [mode, setMode] = useState<'device' | 'manual' | 'map'>('device');
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState(''); const [error, setError] = useState('');
  const container = useRef<HTMLDivElement>(null); const map = useRef<L.Map | null>(null); const marker = useRef<L.CircleMarker | null>(null);
  const callback = useRef(onChange); callback.current = onChange;
  const request = useRef(0); useEffect(() => () => { request.current++; }, []);
  useEffect(() => { if (!active) { request.current++; setBusy(false); } }, [active]);
  useEffect(() => {
    if (!active || mode !== 'map' || !container.current) return;
    const instance = L.map(container.current, { zoomAnimation: false, fadeAnimation: false }).setView([4.15, -73.64], 6); map.current = instance;
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(instance);
    tiles.on('tileerror', () => setMessage('No se pudo cargar el fondo del mapa. Puedes ingresar coordenadas o volver a intentar con conexión.'));
    instance.on('click', (e: L.LeafletMouseEvent) => {
      // Leaflet allows horizontal world wrapping. Normalize longitudes to WGS84.
      const point = e.latlng.wrap();
      request.current++; setBusy(false);
      callback.current({ lat: Math.max(-90, Math.min(90, point.lat)).toFixed(6), lng: point.lng.toFixed(6), source: 'map', uncertaintyM: '' });
    });
    const observer = new ResizeObserver(() => instance.invalidateSize()); observer.observe(container.current);
    return () => { observer.disconnect(); instance.stop(); instance.remove(); map.current = null; marker.current = null; };
  }, [mode, active]);
  useEffect(() => {
    if (!map.current) return;
    marker.current?.remove(); marker.current = null;
    if (lat === '' || lng === '' || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lng)) || Math.abs(Number(lat)) > 90 || Math.abs(Number(lng)) > 180) return;
    const point: L.LatLngTuple = [Number(lat), Number(lng)];
    marker.current = L.circleMarker(point, { radius: 9, color: '#34207d', fillColor: '#91f1b3', fillOpacity: 1 }).addTo(map.current);
    map.current.setView(point, Math.max(map.current.getZoom(), 13), { animate: false });
  }, [lat, lng, mode, active]);
  function locate() {
    setError(''); setMessage('');
    const token = ++request.current; setBusy(true);
    getDeviceLocation().then(point => {
      if (request.current !== token) return;
      callback.current(point as LocationSelection);
      setBusy(false); setMessage(`Ubicación obtenida.${point.uncertaintyM ? ` Incertidumbre aproximada: ${Math.round(Number(point.uncertaintyM))} m.` : ''} Comprueba que corresponda al lugar del hallazgo.`);
    }).catch(failure => {
      if (request.current !== token) return;
      setBusy(false); setError(failure.message + ' Puedes volver a intentar, seleccionar un punto en el mapa o escribir las coordenadas.');
    });
  }
  return <section className="location-picker" aria-label="Ubicación del hallazgo"><div className="segmented-control">{[['device', 'Mi dispositivo'], ['manual', 'Coordenadas'], ['map', 'Seleccionar en mapa']].map(([key, label]) => <button key={key} type="button" aria-pressed={mode === key} className={mode === key ? 'active' : ''} onClick={() => { request.current++; setBusy(false); setMode(key as typeof mode); setError(''); setMessage(''); }}>{label}</button>)}</div>
    {mode === 'device' && <div className="location-prompt"><LocateFixed size={28} /><div><strong>Ubica el hallazgo desde tu dispositivo</strong><p>El navegador pedirá permiso. Si estás en otro lugar, usa el mapa o las coordenadas del sitio.</p><button type="button" className="btn primary small" disabled={busy} onClick={locate}>{busy ? 'Obteniendo ubicación…' : 'Usar mi ubicación'}</button></div></div>}
    {mode === 'map' && <><p className="muted">Haz clic en el lugar del hallazgo. También puedes ingresar coordenadas debajo para usar el teclado.</p><div className="location-map" ref={container} aria-label="Mapa para seleccionar la ubicación" /></>}
    {error && <Notice error>{error}</Notice>}{message && <Notice>{message}</Notice>}
    <div className="form-grid"><label className="field">Latitud<input type="number" min={-90} max={90} step="any" value={lat} onChange={e => { request.current++; setBusy(false); onChange({ lat: e.target.value, lng, source: 'manual', uncertaintyM: '' }); }} placeholder="4.150000" /></label><label className="field">Longitud<input type="number" min={-180} max={180} step="any" value={lng} onChange={e => { request.current++; setBusy(false); onChange({ lat, lng: e.target.value, source: 'manual', uncertaintyM: '' }); }} placeholder="-73.640000" /></label></div><p className="field-help"><MapPin size={14} />WGS84 · Grados decimales. Puedes registrar el sitio sin coordenadas si aún no las conoces.</p>
  </section>;
}
