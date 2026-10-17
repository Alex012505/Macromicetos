import { normalizeDemoImage } from './assets.mjs';
import { referencePhotoCredit } from './photo-credits.mjs';

export function migrateOccurrence(o, baseUrl) {
  const legacyDiameter = (o.measurements || []).find(m => ['diámetro del sombrero', 'diametro_sombrero'].includes(m.name.toLowerCase()));
  const morphology = o.morphology ?? (legacyDiameter ? [{ type: 'diametro_sombrero', value: legacyDiameter.value, unit: legacyDiameter.unit || 'cm' }] : []);
  const images = (o.images || []).map(image => normalizeDemoImage(image, baseUrl));
  const photos = (o.photos || []).map(p => ({ ...p, url: normalizeDemoImage(p.url, baseUrl) }));
  for (const url of images) { const credit = referencePhotoCredit(url); if (credit && !photos.some(p => p.url === url)) photos.push({ url, photoType: 'habitus', ...credit }); }
  return { ...o, eventDate: o.eventDate ?? o.date, morphology,
    measurements: o.morphology == null && legacyDiameter ? o.measurements.filter(m => m !== legacyDiameter) : (o.measurements || []),
    images, photos,
  };
}
