import { morphologyTypes, morphologyLabel } from './morphology.mjs';

const states = { verified: 'Verificado', pending: 'En revisión', rejected: 'Requiere ajustes', unknown: 'Sin estado' };
export const taxonHeaders = ['ID taxón', 'Nombre científico', 'Nombre común', 'Rango', 'Reino', 'División', 'Clase', 'Orden', 'Familia', 'Género', 'Epíteto específico', 'ID taxonómico externo', 'Notas taxonómicas'];
export const taxonCells = t => t ? [t.id, t.scientificName, t.commonName, t.rank || 'species', t.kingdom, t.phylum, t.className, t.order, t.family, t.genus, t.specificEpithet || '', t.externalTaxonId || '', t.remarks] : taxonHeaders.map(() => '');
const factText = (facts, type) => { const m = (facts || []).find(m => m.type === type); return m ? `${m.value}${m.unit ? ` ${m.unit}` : ''}` : ''; };
export function speciesRows(taxa, records) {
  return [ [...taxonHeaders, 'Estado', 'Observaciones', ...morphologyTypes.map(([, label]) => label)],
    ...taxa.map(t => [...taxonCells(t), states[t.status] || '', records.filter(o => o.taxonId === t.id).length, ...morphologyTypes.map(([type]) => factText(t.morphology, type))]) ];
}
export function occurrenceRows(records, taxa) {
  return [[...taxonHeaders, 'ID hallazgo', 'ID evento', 'Tipo de registro', 'ID externo del hallazgo', 'Fecha de observación', 'Registrado por', 'Identificado por', 'Fecha de identificación', 'País', 'Departamento', 'Municipio', 'Localidad', 'Latitud WGS84', 'Longitud WGS84', 'Incertidumbre (m)', 'Elevación (m)', 'Hábitat', 'Sustrato', 'Estado', 'Notas del hallazgo', 'Código de campo', 'Tipo de evento', 'Protocolo', 'Esfuerzo de muestreo', 'Notas de ubicación', 'Notas del evento', 'Medidas ambientales', ...morphologyTypes.map(([, label]) => label)],
    ...records.map(o => [...taxonCells(taxa.find(t => t.id === o.taxonId)), o.id, o.eventId, o.basisOfRecord || '', o.externalOccurrenceId || '', o.eventDate || o.date, o.recordedBy || '', o.author, o.date, o.country || '', o.department, o.municipality || '', o.locality, o.lat, o.lng, o.uncertaintyM, o.elevationM, o.habitat, o.substrate, states[o.status], o.remarks, o.fieldNumber || '', o.eventType || '', o.samplingProtocol || '', o.samplingEffort || '', o.locationRemarks || '', o.eventRemarks || '', (o.measurements || []).map(m => `${m.scope === 'event' ? 'Evento' : 'Hallazgo'}: ${m.name} = ${m.value} ${m.unit || ''}`).join('; '), ...morphologyTypes.map(([type]) => factText(o.morphology, type))])];
}
export function morphologyRows(taxa, records) {
  const rows = [['Ámbito', 'ID', 'Nombre científico', 'Rasgo', 'Valor', 'Unidad', 'Fecha de evaluación', 'Notas']];
  for (const t of taxa) for (const m of t.morphology || []) rows.push(['Especie', t.id, t.scientificName, morphologyLabel(m.type), m.value, m.unit || '', m.determinedDate || '', m.remarks || '']);
  for (const o of records) for (const m of o.morphology || []) rows.push(['Hallazgo', o.id, taxa.find(t => t.id === o.taxonId)?.scientificName || '', morphologyLabel(m.type), m.value, m.unit || '', m.determinedDate || '', m.remarks || '']);
  return rows;
}
export function csvText(rows) {
  const cell = value => {
    let str = value == null ? '' : String(value);
    // Spreadsheet formula injection can begin after tabs, newlines or spaces.
    if (typeof value !== 'number' && /^[\s\uFEFF]*[=+@-]/.test(str)) str = "'" + str;
    return `"${str.replaceAll('"', '""')}"`;
  };
  return '\uFEFF' + rows.map(row => row.map(cell).join(',')).join('\r\n');
}
