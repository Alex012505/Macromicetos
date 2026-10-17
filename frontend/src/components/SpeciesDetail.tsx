import { useEffect, useState } from 'react';
import { ChevronLeft, Download, ImagePlus, Pencil } from 'lucide-react';
import { api, config } from '../lib/api';
import { createSpeciesPdf, downloadBlob } from '../lib/downloads';
import { morphologyLabel } from '../lib/morphology.mjs';
import type { Occurrence, Taxon } from '../types';
import { Busy, Empty, Notice, Photo, StatusBadge } from './UI';
import OccurrenceMap from './OccurrenceMap';
import RecordDetails, { DetailFields } from './RecordDetails';
import ExportButtons from './ExportButtons';

const tabs = ['Taxonomía', 'Morfología', 'Ecología', 'Geografía', 'Multimedia', 'Bibliografía', 'Socioecología'] as const;
type Tab = typeof tabs[number];
export default function SpeciesDetail({ taxon, taxonId, records, onBack, onEdit, onEditTaxon, onUpload, canEditRecord, canReadSensitive }: {
  taxon?: Taxon; taxonId: string; records: Occurrence[]; onBack: () => void; onEdit?: (o: Occurrence) => void;
  onEditTaxon?: (t: Taxon) => void; onUpload?: (o: Occurrence) => void; canEditRecord: (o: Occurrence) => boolean; canReadSensitive: boolean;
}) {
  const [loaded, setLoaded] = useState<Taxon>(); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [pdfBusy, setPdfBusy] = useState(false); const [pdfMessage, setPdfMessage] = useState('');
  const [tab, setTab] = useState<Tab>('Taxonomía'); const [selectedId, setSelectedId] = useState('');
  const t = loaded || taxon;
  useEffect(() => {
    setLoaded(undefined); setError(''); setTab('Taxonomía'); setSelectedId(''); setPdfMessage('');
    if (config.demo) return;
    let active = true; setBusy(true);
    api.taxon(taxonId).then(t => { if (active) setLoaded(t); }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [taxonId, taxon]);
  async function pdf() {
    if (!t) return; setPdfBusy(true); setPdfMessage('');
    try { const result = await createSpeciesPdf(t, records); downloadBlob(result.blob, result.filename); setPdfMessage(result.warnings.length ? `Ficha descargada. No se pudieron incorporar ${result.warnings.length} fotografías; comprueba su disponibilidad y vuelve a descargarla.` : 'Ficha PDF descargada con los datos y fotografías disponibles.'); }
    catch { setPdfMessage('No se pudo generar la ficha PDF. Intenta de nuevo.'); } finally { setPdfBusy(false); }
  }
  if (busy) return <Busy />;
  if (!t) return <><button className="text-button" onClick={onBack}><ChevronLeft size={17} />Volver al catálogo</button>{error ? <Notice error>{error}</Notice> : <Empty title="No encontramos esta especie" />}</>;
  const occurrences = records.filter(o => o.taxonId === t.id);
  const selected = occurrences.find(o => o.id === selectedId) || occurrences[0];
  const images = [...new Set([t.image, ...occurrences.flatMap(o => o.images)].filter((u): u is string => Boolean(u)))];
  const allowedTabs = tabs.filter(name => name !== 'Socioecología' || canReadSensitive);
  return <><button className="text-button back-link" onClick={onBack}><ChevronLeft size={17} />Volver al catálogo</button>{error && <Notice error>{error}</Notice>}<section className="panel species-profile"><div className="profile-header"><Photo src={t.image || images[0]} name={t.scientificName} /><div><span className="eyebrow">FICHA DE ESPECIE · DARWIN CORE</span><h1 className="scientific-name">{t.scientificName}</h1><p className="profile-common-name">{t.commonName || 'Sin nombre común registrado'}</p><div className="profile-meta"><StatusBadge status={t.status} /><span>{t.family || 'Sin familia registrada'}</span><span>{occurrences.length} observaciones</span></div></div></div>
    <div className="profile-actions"><button className="btn primary" disabled={pdfBusy} onClick={() => void pdf()}><Download size={16} />{pdfBusy ? 'Preparando ficha…' : 'Descargar ficha PDF'}</button><ExportButtons scope="species" taxa={[t]} records={occurrences} />{onEditTaxon && <button className="btn" onClick={() => onEditTaxon(t)}><Pencil size={16} />Editar ficha</button>}</div>{pdfMessage && <Notice>{pdfMessage}</Notice>}
    <div className="tabs profile-tabs" role="tablist" aria-label="Secciones de la ficha">{allowedTabs.map(name => <button key={name} role="tab" id={`tab-${name}`} tabIndex={name === tab ? 0 : -1} aria-controls="species-panel" aria-selected={name === tab} className={name === tab ? 'active' : ''} onClick={() => setTab(name)} onKeyDown={e => {
      if (!e.ctrlKey && !e.metaKey && !e.altKey && ['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(e.key)) { e.preventDefault(); const index = e.key === 'Home' ? 0 : e.key === 'End' ? allowedTabs.length - 1 : (allowedTabs.indexOf(tab) + (e.key === 'ArrowRight' ? 1 : -1) + allowedTabs.length) % allowedTabs.length; const next = allowedTabs[index]; setTab(next); document.getElementById(`tab-${next}`)?.focus(); }
    }}>{name}</button>)}</div><div className="profile-content" id="species-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
      {tab === 'Taxonomía' && <><h2>Identificación taxonómica</h2><dl className="detail-fields">{[['Reino', t.kingdom], ['División', t.phylum], ['Clase', t.className], ['Orden', t.order], ['Familia', t.family], ['Género', t.genus], ['Especie', t.scientificName], ['Epíteto específico', t.specificEpithet], ['Rango', t.rank || 'species'], ['Identificador externo', t.externalTaxonId], ['Notas taxonómicas', t.remarks]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd className={['Género', 'Especie', 'Epíteto específico'].includes(label || '') ? 'scientific-name' : ''}>{value || 'Sin dato registrado'}</dd></div>)}</dl>{!!t.participants?.length && <><h3>Responsables taxonómicos</h3>{t.participants.map(p => <DetailFields key={p.id} rows={[[ 'Responsable', p.displayName], ['Afiliación', p.affiliation], ['ORCID', p.orcid]]} />)}</>}</>}
      {tab === 'Morfología' && <><h2>Rasgos generales de la especie</h2>{t.morphology?.length ? t.morphology.map(m => <DetailFields key={m.type} rows={[[morphologyLabel(m.type), `${m.value} ${m.unit || ''}`], ['Fecha de evaluación', m.determinedDate], ['Notas', m.remarks]]} />) : <p className="muted">No hay rasgos generales registrados.</p>}<h2>Morfología por hallazgo</h2>{occurrences.some(o => o.morphology?.length) ? occurrences.filter(o => o.morphology?.length).map(o => <article className="measurement-block" key={o.id}><h3>{o.locality || o.id} · {o.eventDate || o.date}</h3>{o.morphology!.map(m => <DetailFields key={m.type} rows={[[morphologyLabel(m.type), `${m.value} ${m.unit || ''}`], ['Fecha de evaluación', m.determinedDate], ['Notas', m.remarks]]} />)}</article>) : <p className="muted">No hay rasgos de especímenes registrados. Puedes añadirlos al crear o editar un hallazgo.</p>}</>}
      {tab === 'Ecología' && <><h2>Hallazgos y contexto ecológico</h2>{occurrences.length ? occurrences.map(o => <details className="record-details" key={o.id}><summary>{o.locality || o.id} · {o.eventDate || o.date || 'Sin fecha'}</summary><RecordDetails record={o} /><div className="heading-actions">{onEdit && canEditRecord(o) && <button className="btn small" onClick={() => onEdit(o)}><Pencil size={14} />Editar hallazgo</button>}{onUpload && canEditRecord(o) && <button className="btn small" onClick={() => onUpload(o)}><ImagePlus size={14} />Añadir fotos</button>}</div></details>) : <Empty title="Sin hallazgos asociados" />}</>}
      {tab === 'Geografía' && <><h2>Distribución de las observaciones</h2>{occurrences.length ? <><OccurrenceMap records={occurrences} taxa={[t]} onSelect={o => setSelectedId(o.id)} /><p className="muted">{occurrences.filter(o => o.lat != null && o.lng != null).length} de {occurrences.length} hallazgos con coordenadas.</p>{selected && <DetailFields rows={[[selected.locality || 'Hallazgo', selected.lat != null && selected.lng != null ? `${selected.lat}, ${selected.lng} · WGS84` : 'Sin coordenadas registradas'], ['Incertidumbre (m)', selected.uncertaintyM], ['Elevación (m)', selected.elevationM]]} />}</> : <Empty title="Sin observaciones geográficas" />}</>}
      {tab === 'Multimedia' && <><h2>Fotografías de la especie</h2>{onUpload && occurrences.some(canEditRecord) && <div className="photo-upload-links">{occurrences.filter(canEditRecord).map(o => <button className="btn small" key={o.id} onClick={() => onUpload(o)}><ImagePlus size={14} />Añadir fotos: {o.locality || o.id} · {o.eventDate || o.date}</button>)}</div>}{images.length ? <div className="detail-gallery">{images.map((src, i) => { const record = occurrences.find(o => o.images.includes(src)); const p = record?.photos?.find(p => p.url === src); return <figure key={src}><Photo src={src} name={`${t.scientificName}, fotografía ${i + 1}`} /><figcaption>{record?.locality || 'Imagen del catálogo'} · {p?.photographer || 'Fotografía de referencia'} · {p?.license || 'Consultar créditos de origen'}</figcaption></figure>; })}</div> : <Empty title="Aún no hay fotografías asociadas" />}</>}
      {tab === 'Bibliografía' && <><h2>Fuentes y referencias</h2>{t.sources?.length ? t.sources.map(s => <article className="entry-card" key={s.id}><h3>{s.title || 'Sin título'}</h3><DetailFields rows={[[ 'Tipo', s.sourceType], ['Autores', s.authors], ['Año', s.year], ['DOI', s.doi]]} /></article>) : <Empty title="Sin referencias registradas">Añade las fuentes desde la edición de la ficha.</Empty>}</>}
      {tab === 'Socioecología' && canReadSensitive && <><h2>Conocimiento y usos reportados</h2><p className="muted">Información de investigación. Las entrevistas no se incluyen en las descargas públicas.</p>{t.knowledge?.length ? t.knowledge.map((s, i) => <details className="record-details" key={s.id}><summary>Entrevista {i + 1} · {s.interviewDate}</summary><DetailFields rows={[
        ['Entrevistador/a', s.interviewer], ['Consentimiento otorgado', s.consentGiven ? 'Sí' : 'No'], ['Tipo de consentimiento', s.consentType], ['Anonimato', s.anonymityLevel], ['Rango de edad', s.ageRange], ['Género (persona)', s.gender], ['Ocupación', s.occupation], ['Departamento', s.stateProvince], ['Municipio', s.municipality], ['Vereda', s.village], ['Conoce los hongos', s.knowsFungi ? 'Sí' : 'No'], ['Nombre local', s.localName], ['Origen del conocimiento', s.learningSource], ['Reconocimiento', s.recognitionCues], ['Lugares', s.foundInPlaces], ['Estacionalidad', s.seasonality], ['Meses', s.months], ['Prácticas de seguridad', s.safetyPractices], ['Relatos', s.mythsStories], ['Identidad cultural', s.culturalIdentity], ['Notas', s.remarks],
      ]} />{s.uses.map(u => <DetailFields key={u.id} rows={[[ 'Categoría de uso', u.useCategory], ['Importancia', u.importance], ['Preparación', u.preparationMethod], ['Afección reportada', u.ailment], ['Dosificación reportada', u.dosage], ['Contraindicaciones reportadas', u.contraindications], ['Recomendaciones de la fuente', u.recommendations]]} />)}</details>) : <Empty title="Sin entrevistas registradas" />}</>}
    </div></section></>;
}
