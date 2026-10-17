// The values are the PostgreSQL ecological.morphology_type_enum, not UI labels.
export const morphologyTypes = [
  ['tipo_himenio', 'Tipo de himenio'], ['tipo_laminas', 'Tipo de láminas'],
  ['forma_poros', 'Forma de los poros'], ['diametro_sombrero', 'Diámetro del sombrero'],
  ['forma_sombrero', 'Forma del sombrero'], ['superficie_sombrero', 'Superficie del sombrero'],
  ['borde_sombrero', 'Borde del sombrero'], ['color_sombrero', 'Color del sombrero'],
  ['forma_pie', 'Forma del pie'], ['color_pie', 'Color del pie'],
  ['posicion_pie', 'Posición del pie'], ['ornamentacion_pie', 'Ornamentación del pie'],
  ['superficie_pie', 'Superficie del pie'], ['presencia_anillo', 'Presencia de anillo'],
  ['tipo_anillo', 'Tipo de anillo'], ['presencia_volva', 'Presencia de volva'],
  ['cambio_color_corte', 'Cambio de color al corte'], ['habito_crecimiento', 'Hábito de crecimiento'],
];
export const morphologyLabel = type => morphologyTypes.find(([key]) => key === type)?.[1] || type;
export function validateMorphology(facts = []) {
  const seen = new Set();
  for (const fact of facts) {
    if (!morphologyTypes.some(([type]) => type === fact.type)) throw new Error('Selecciona un rasgo morfológico válido.');
    if (seen.has(fact.type)) throw new Error(`El rasgo «${morphologyLabel(fact.type)}» está repetido.`);
    seen.add(fact.type);
    if (!fact.value?.trim()) throw new Error(`Falta el valor de «${morphologyLabel(fact.type)}».`);
    if (fact.type === 'diametro_sombrero' && !['cm', 'mm'].includes(fact.unit)) throw new Error('Indica cm o mm para el diámetro del sombrero.');
  }
}
export function validateCoordinates(lat, lng) {
  const empty = v => v === '' || v == null;
  if (empty(lat) !== empty(lng)) throw new Error('Ingresa latitud y longitud juntas, o deja ambas vacías.');
  if (empty(lat)) return { lat: null, lng: null };
  const latitude = Number(lat), longitude = Number(lng);
  if (!Number.isFinite(latitude) || Math.abs(latitude) > 90 || !Number.isFinite(longitude) || Math.abs(longitude) > 180) throw new Error('Las coordenadas WGS84 deben estar entre -90 y 90 de latitud y -180 y 180 de longitud.');
  return { lat: latitude, lng: longitude };
}
