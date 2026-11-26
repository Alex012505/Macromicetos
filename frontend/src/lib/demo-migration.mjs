import { normalizeDemoImage } from './assets.mjs';
import { referencePhotoCredit } from './photo-credits.mjs';
import { measurementTypes, measurementUnit } from './measurements.mjs';

const LEGACY_MEASUREMENTS = {
  temperatura: 'temperature', humedad: 'relativeHumidity', 'humedad relativa': 'relativeHumidity',
  'presión atmosférica': 'atmosphericPressure', presion: 'atmosphericPressure', altitud: 'altitude',
  'punto de rocío': 'dewPoint', 'índice de calor': 'heatIndex', 'velocidad del viento': 'windSpeed',
  'sensación térmica': 'windChill',
};
function migrateMeasurement(m) {
  const type = m.type || LEGACY_MEASUREMENTS[String(m.name || '').trim().toLowerCase()];
  if (!measurementTypes.some(([key]) => key === type)) return null;
  return { type, value: String(m.value ?? ''), unit: m.unit || measurementUnit(type), method: m.method || '', remarks: m.remarks || '' };
}

export function migrateDemoUser(user) {
  const role = ({ readonly_user: 'viewer', researcher: 'analyst', field_collector: 'analyst' })[user.role] || user.role;
  return { ...user, role: ['viewer', 'analyst', 'curator', 'admin'].includes(role) ? role : 'viewer' };
}

export function migrateOccurrence(o, baseUrl) {
  const legacyDiameter = (o.measurements || []).find(m => ['diámetro del sombrero', 'diametro_sombrero'].includes(String(m.name || '').toLowerCase()));
  const morphology = o.morphology ?? (legacyDiameter ? [{ type: 'diametro_sombrero', value: legacyDiameter.value, unit: legacyDiameter.unit || 'cm' }] : []);
  const images = (o.images || []).map(image => normalizeDemoImage(image, baseUrl));
  const photos = (o.photos || []).map(p => ({ ...p, url: normalizeDemoImage(p.url, baseUrl) }));
  for (const url of images) { const credit = referencePhotoCredit(url); if (credit && !photos.some(p => p.url === url)) photos.push({ url, photoType: 'habitus', ...credit }); }
  return { ...o, eventDate: o.eventDate ?? o.date, morphology,
    measurements: (o.measurements || []).map(migrateMeasurement).filter(Boolean),
    images, photos,
  };
}
