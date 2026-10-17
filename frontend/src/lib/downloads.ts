import type { Occurrence, Taxon } from '../types';
import { csvText, occurrenceRows, speciesRows, morphologyRows } from './export-data.mjs';
import { config } from './api';
import { morphologyLabel } from './morphology.mjs';
import { isPdfImageUrl } from './pdf-images.mjs';
import { referencePhotoCredit } from './photo-credits.mjs';
import { statusNames } from '../types';

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob); const a = document.createElement('a');
  a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove();
  // Keep the object URL alive while the browser accepts the download.
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
type Table = (string | number | null | undefined)[][];
export async function exportData(format: 'csv' | 'xlsx', scope: 'species' | 'records', taxa: Taxon[], records: Occurrence[]) {
  const rows: Table = scope === 'species' ? speciesRows(taxa, records) : occurrenceRows(records, taxa);
  const filename = `macromicetos-${scope === 'species' ? 'especies' : 'registros'}${config.demo ? '-DEMO' : ''}`;
  if (format === 'csv') { downloadBlob(new Blob([csvText(rows)], { type: 'text/csv;charset=utf-8' }), `${filename}.csv`); return; }
  const { default: ExcelJS } = await import('exceljs');
  const book = new ExcelJS.Workbook(); book.creator = 'Macromicetos'; book.created = new Date();
  const relevantTaxa = scope === 'species' ? taxa : taxa.filter(t => records.some(o => o.taxonId === t.id));
  const tables: [string, Table, number[]][] = [
    ['Especies', speciesRows(relevantTaxa, records), [2, 10, 11]],
    ['Hallazgos', occurrenceRows(records, taxa), [2, 10, 11]],
    ['Morfología', morphologyRows(relevantTaxa, records), [3]],
  ];
  for (const [name, values, italicColumns] of tables) {
    const sheet = book.addWorksheet(name); sheet.addRows(values.map(row => row.map(v => v ?? '')));
    sheet.views = [{ state: 'frozen', ySplit: 1 }]; sheet.autoFilter = { from: { row: 1, column: 1 }, to: { row: values.length, column: values[0].length } };
    sheet.getRow(1).height = 34; sheet.getRow(1).eachCell(cell => { cell.font = { bold: true, color: { argb: 'FFFFFFFF' } }; cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF34207D' } }; cell.alignment = { vertical: 'middle', wrapText: true }; });
    sheet.columns.forEach(column => { column.width = 26; });
    for (let i = 2; i <= values.length; i++) {
      sheet.getRow(i).eachCell(cell => { cell.alignment = { vertical: 'top', wrapText: true }; if (i % 2 === 0) cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F7F3' } }; });
      italicColumns.forEach(column => { sheet.getCell(i, column).font = { italic: true }; });
    }
  }
  const buffer = await book.xlsx.writeBuffer();
  downloadBlob(new Blob([new Uint8Array(buffer)], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), `${filename}.xlsx`);
}

async function imageForPdf(url: string): Promise<{ data: string; width: number; height: number }> {
  if (!isPdfImageUrl(url)) throw new Error('URL de imagen no válida');
  return new Promise((resolve, reject) => {
    const img = new Image(); img.crossOrigin = 'anonymous';
    const timer = setTimeout(() => { img.src = ''; reject(new Error('Tiempo agotado al cargar la fotografía')); }, 15000);
    img.onload = () => {
      clearTimeout(timer);
      try {
        const factor = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
        const canvas = document.createElement('canvas'); canvas.width = Math.max(1, Math.round(img.naturalWidth * factor)); canvas.height = Math.max(1, Math.round(img.naturalHeight * factor));
        const context = canvas.getContext('2d'); if (!context) throw new Error('No se pudo preparar la foto');
        context.fillStyle = '#ffffff'; context.fillRect(0, 0, canvas.width, canvas.height); context.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve({ data: canvas.toDataURL('image/jpeg', .88), width: canvas.width, height: canvas.height });
      } catch (e) { reject(e); }
    };
    img.onerror = () => { clearTimeout(timer); reject(new Error('Fotografía no disponible o sin permiso CORS')); };
    img.src = url;
  });
}
export async function createSpeciesPdf(t: Taxon, occurrences: Occurrence[]) {
  const { jsPDF } = await import('jspdf');
  const pdf = new jsPDF({ unit: 'mm', format: 'a4' }); let y = 22;
  const records = occurrences.filter(o => o.taxonId === t.id); const warnings: string[] = [];
  const clean = (value: unknown) => String(value ?? '').replace(/[\u2010-\u2015]/g, '-');
  function newPage() { pdf.addPage(); y = 22; }
  function ensure(height: number) { if (y + height > 277) newPage(); }
  function text(value: unknown, style = 'normal', size = 10) {
    pdf.setFont('helvetica', style); pdf.setFontSize(size); pdf.setTextColor(52, 48, 63);
    const lines: string[] = pdf.splitTextToSize(clean(value), 174);
    for (const line of lines) { ensure(size * .5 + 2); pdf.text(line, 18, y); y += size * .45 + 1; }
    y += 2;
  }
  function heading(label: string) { ensure(20); y += 4; text(label, 'bold', 13); }
  function field(label: string, value: unknown, italic = false) { if (value !== '' && value != null) text(`${label}: ${value}`, italic ? 'italic' : 'normal'); }
  function morphology(items: Taxon['morphology']) { for (const m of items || []) { field(morphologyLabel(m.type), `${m.value} ${m.unit || ''}`); field('Evaluación', m.determinedDate); field('Notas', m.remarks); } }
  pdf.setProperties({ title: `Ficha técnica - ${t.scientificName}`, author: 'Macromicetos' });
  text('MACROMICETOS / FICHA TÉCNICA', 'bold', 10); text(t.scientificName, 'bolditalic', 22); text(t.commonName || 'Sin nombre común registrado', 'normal', 12);
  text(`Generada: ${new Intl.DateTimeFormat('es-CO', { timeZone: 'America/Bogota' }).format(new Date())}${config.demo ? ' | DATOS DE DEMOSTRACIÓN' : ''}`, 'normal', 9);
  heading('Taxonomía');
  for (const [label, value] of [['Estado', statusNames[t.status]], ['Reino', t.kingdom], ['División', t.phylum], ['Clase', t.className], ['Orden', t.order], ['Familia', t.family], ['Género', t.genus], ['Epíteto específico', t.specificEpithet], ['Rango', t.rank || 'species'], ['ID taxonómico', t.externalTaxonId], ['Notas', t.remarks]]) field(label || '', value, label === 'Género' || label === 'Epíteto específico');
  heading('Morfología general'); if (!t.morphology?.length) text('Sin rasgos generales registrados.'); morphology(t.morphology);
  heading('Observaciones de campo'); if (!records.length) text('No hay hallazgos asociados.');
  for (const o of records) {
    heading(`${o.locality || 'Hallazgo'} / ${o.eventDate || o.date || 'Sin fecha'}`);
    for (const [label, value] of [['ID', o.id], ['Estado', statusNames[o.status]], ['Fecha y hora del hallazgo', o.occurrenceDate], ['Tipo de evento', o.eventType], ['Tipo de registro', o.basisOfRecord], ['ID externo', o.externalOccurrenceId], ['País', o.country], ['Departamento', o.department], ['Municipio', o.municipality], ['Hábitat', o.habitat], ['Sustrato', o.substrate], ['Registrado por', o.recordedBy], ['Identificado por', o.author], ['Fecha de identificación', o.date], ['Elevación (m)', o.elevationM], ['Incertidumbre (m)', o.uncertaintyM], ['Código de campo', o.fieldNumber], ['Protocolo', o.samplingProtocol], ['Esfuerzo', o.samplingEffort], ['Notas del sitio', o.locationRemarks], ['Notas de la salida', o.eventRemarks], ['Notas del hallazgo', o.remarks]]) field(String(label), value);
    if (o.lat != null && o.lng != null) field('Coordenadas WGS84', `${o.lat}, ${o.lng}`);
    morphology(o.morphology);
    for (const m of o.measurements) field(`${m.name} (${m.scope === 'event' ? 'evento' : 'hallazgo'})`, `${m.value} ${m.unit || ''}`);
  }
  heading('Fuentes bibliográficas'); if (!t.sources?.length) text('Sin referencias registradas.');
  for (const s of t.sources || []) text([s.authors, s.year, s.title, s.doi ? `DOI: ${s.doi}` : ''].filter(Boolean).join(' · '));
  const photographs: { url: string; caption: string }[] = [];
  const seen = new Set<string>();
  for (const o of records) for (const url of o.images) {
    if (seen.has(url)) continue; seen.add(url); const p = o.photos?.find(p => p.url === url) || referencePhotoCredit(url);
    photographs.push({ url, caption: [`Hallazgo: ${o.locality || o.id}`, o.photos?.find(photo => photo.url === url)?.photoType, p?.photographer ? `Foto: ${p.photographer}` : '', p?.rightsHolder ? `Titular: ${p.rightsHolder}` : '', p?.license ? `Licencia: ${p.license}` : 'Sin licencia declarada', p?.sourceUrl ? `Fuente: ${p.sourceUrl}` : '', ...(o.photos?.find(photo => photo.url === url)?.credits || []).map(c => `${c.displayName} (${c.role})`)].filter(Boolean).join(' · ') });
  }
  if (t.image && !seen.has(t.image)) { const credit = referencePhotoCredit(t.image); photographs.unshift({ url: t.image, caption: ['Imagen de referencia del catálogo', credit?.photographer, credit?.license, credit?.sourceUrl].filter(Boolean).join(' · ') }); }
  heading('Fotografías'); if (!photographs.length) text('No hay fotografías disponibles.');
  if (config.demo) text('Las fotografías de referencia no documentan las observaciones ficticias de esta demostración.', 'normal', 9);
  for (const [i, p] of photographs.entries()) {
    try {
      const img = await imageForPdf(p.url); const scale = Math.min(174 / img.width, 100 / img.height); const w = img.width * scale, h = img.height * scale;
      ensure(h + 25); pdf.addImage(img.data, 'JPEG', 18 + (174 - w) / 2, y, w, h); y += h + 5; text(`${i + 1}. ${p.caption}`, 'normal', 9);
    } catch { warnings.push(`Fotografía ${i + 1}`); text(`Fotografía ${i + 1}: no se pudo incorporar. ${p.caption}`, 'normal', 9); }
  }
  for (let page = 1; page <= pdf.getNumberOfPages(); page++) {
    pdf.setPage(page); pdf.setFont('helvetica', 'normal'); pdf.setFontSize(8); pdf.setTextColor(105, 99, 116); pdf.text(`Macromicetos | ${page} / ${pdf.getNumberOfPages()}`, 18, 288);
  }
  return { blob: pdf.output('blob'), warnings, filename: `ficha-${t.scientificName.replace(/[^\p{L}\p{N}-]+/gu, '-').toLowerCase().slice(0, 100)}${config.demo ? '-DEMO' : ''}.pdf` };
}
