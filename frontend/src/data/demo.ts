import type { Dataset, Taxon, Occurrence, Role, User } from '../types';

// Los nombres y taxonomía son ejemplos de interfaz. Localidades, fechas, personas,
// estados y medidas son ficticios; no constituyen observaciones científicas.
const rows = [
  ['Pleurotus ostreatus', 'Orellana', 'Pleurotaceae', 'Agaricales', '/images/pleurotus.jpg'],
  ['Trametes versicolor', 'Cola de pavo', 'Polyporaceae', 'Polyporales', '/images/trametes.jpg'],
  ['Pycnoporus sanguineus', 'Hongo rojo de la madera', 'Polyporaceae', 'Polyporales', ''],
  ['Schizophyllum commune', 'Hongo de láminas divididas', 'Schizophyllaceae', 'Agaricales', ''],
  ['Auricularia auricula-judae', 'Oreja de palo', 'Auriculariaceae', 'Auriculariales', ''],
  ['Lentinus crinitus', 'Hongo de sombrero velloso', 'Polyporaceae', 'Polyporales', ''],
  ['Ganoderma lucidum', 'Ganoderma', 'Ganodermataceae', 'Polyporales', ''],
  ['Coprinellus disseminatus', 'Coprinelo', 'Psathyrellaceae', 'Agaricales', ''],
];
export const demoTaxa: Taxon[] = rows.map((r, i) => ({
  id: `demo-taxon-${i + 1}`, scientificName: r[0], commonName: r[1], family: r[2], order: r[3],
  image: r[4] || undefined, kingdom: 'Fungi', phylum: 'Basidiomycota', className: 'Agaricomycetes',
  genus: r[0].split(' ')[0], remarks: 'Ficha ilustrativa para evaluar la navegación. La información definitiva debe provenir del catálogo del equipo.',
  status: i === 2 || i === 5 ? 'pending' : 'verified',
}));
const places = [
  ['Meta', 'Villavicencio · Bosque de galería', 4.15, -73.64],
  ['Casanare', 'Yopal · Sendero de muestreo', 5.34, -72.4],
  ['Arauca', 'Tame · Ribera del río', 6.46, -71.73],
  ['Vichada', 'Puerto Carreño · Bosque secundario', 6.18, -67.49],
] as const;
export const demoOccurrences: Occurrence[] = Array.from({ length: 12 }, (_, i) => {
  const taxon = demoTaxa[i % demoTaxa.length];
  const place = places[i % 4];
  return {
    id: `demo-occ-${i + 1}`, taxonId: taxon.id, eventId: `demo-event-${i + 1}`, ownerId: `demo-u${i % 3 + 1}`,
    author: ['Laura Martínez', 'Andrés Rojas', 'Camila Torres'][i % 3],
    date: `2026-09-${String(30 - i).padStart(2, '0')}`, department: place[0], locality: place[1],
    lat: place[2] + (i > 3 ? i * 0.024 : 0), lng: place[3] + (i > 3 ? i * 0.018 : 0),
    substrate: ['Madera muerta', 'Hojarasca', 'Madera muerta', 'Suelo orgánico'][i % 4],
    habitat: i % 2 ? 'Bosque secundario' : 'Bosque de galería',
    remarks: 'Observación de demostración. Las coordenadas y los datos de campo son ficticios.',
    status: i === 2 || i === 5 || i === 8 ? 'pending' : i === 10 ? 'rejected' : 'verified',
    images: taxon.image ? [taxon.image] : [],
    measurements: [{ name: 'Diámetro del sombrero', value: '4–7', unit: 'cm' }],
  };
});
export const demoUsers = [
  { id: 'demo-u1', name: 'Laura Martínez', email: 'laura@example.org', role: 'researcher' as const },
  { id: 'demo-u2', name: 'Andrés Rojas', email: 'andres@example.org', role: 'curator' as const },
  { id: 'demo-u3', name: 'Camila Torres', email: 'camila@example.org', role: 'admin' as const },
];
const STORAGE_KEY = 'macromicetos-demo-dataset-v2';
const LEGACY_KEY = 'virtus-demo-dataset-v1';
export function demoUserForRole(role: Role): User {
  if (role === 'readonly_user') return { id: 'demo-public', name: 'Visitante académico', email: '', role };
  const sample = demoUsers.find(u => u.role === role)!;
  return { ...sample, role };
}
export function loadDemo(): Dataset {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_KEY) || 'null');
    if (data && Array.isArray(data.taxa) && Array.isArray(data.occurrences) && Array.isArray(data.users)) {
      return { ...data, occurrences: data.occurrences.map((o: Occurrence) => ({ ...o, ownerId: o.ownerId || demoUsers.find(u => u.name === o.author)?.id })) };
    }
  } catch { /* A blocked or corrupted browser store must not prevent the demo. */ }
  return structuredClone({ taxa: demoTaxa, occurrences: demoOccurrences, users: demoUsers });
}
export function saveDemo(dataset: Dataset) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(dataset)); }
  catch { throw new Error('No fue posible guardar en el navegador. El almacenamiento está bloqueado o lleno; prueba con una imagen más pequeña.'); }
}
export function resetDemo() {
  try { localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(LEGACY_KEY); }
  catch { throw new Error('El navegador no permitió restablecer la demostración.'); }
}
