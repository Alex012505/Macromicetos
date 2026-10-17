import { validateCoordinates } from './morphology.mjs';
export function getDeviceLocation({ secure = globalThis.isSecureContext, geolocation = globalThis.navigator?.geolocation } = {}) {
  if (!secure || !geolocation) return Promise.reject(new Error('La ubicación del dispositivo requiere HTTPS o localhost y un navegador compatible. Puedes usar el mapa o las coordenadas.'));
  return new Promise((resolve, reject) => {
    geolocation.getCurrentPosition(position => {
      try {
        const c = position.coords; const point = validateCoordinates(c.latitude, c.longitude);
        if (point.lat == null || point.lng == null) throw new Error('El dispositivo no devolvió coordenadas válidas.');
        const accuracy = Number(c.accuracy);
        resolve({ lat: point.lat.toFixed(6), lng: point.lng.toFixed(6), source: 'device', uncertaintyM: Number.isFinite(accuracy) && accuracy >= 0 ? accuracy.toFixed(2) : '', elevationM: c.altitude == null || !Number.isFinite(Number(c.altitude)) ? undefined : Number(c.altitude).toFixed(2) });
      } catch (e) { reject(e); }
    }, failure => {
      reject(new Error(({ 1: 'No se concedió permiso de ubicación.', 2: 'El dispositivo no pudo determinar su ubicación.', 3: 'Se agotó el tiempo de espera de la ubicación.' })[failure.code] || 'No se pudo obtener la ubicación del dispositivo.'));
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
  });
}
