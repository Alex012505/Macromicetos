import { useEffect, useState } from 'react';
import { ChevronLeft, MapPin, Microscope, Pencil } from 'lucide-react';
import { api, config } from '../lib/api';
import type { Occurrence, Taxon } from '../types';
import { Busy, Empty, Notice, Photo, StatusBadge } from './UI';
import OccurrenceMap from './OccurrenceMap';

const tabs = ['Taxonomía', 'Morfología', 'Ecología', 'Geografía', 'Multimedia'] as const;
type Tab = typeof tabs[number];
export default function SpeciesDetail({ taxon, taxonId, records, onBack, onEdit, canEditRecord }: { taxon?: Taxon; taxonId: string; records: Occurrence[]; onBack: () => void; onEdit?: (o: Occurrence) => void; canEditRecord: (o: Occurrence) => boolean }) {
  const [loaded, setLoaded] = useState<Taxon>(); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('Taxonomía'); const [selectedId, setSelectedId] = useState('');
  const t = taxon || loaded;
  useEffect(() => {
    setLoaded(undefined); setError(''); setTab('Taxonomía'); setSelectedId('');
    if (taxon || config.demo) return;
    let active = true; setBusy(true);
    api.taxon(taxonId).then(t => { if (active) setLoaded(t); }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [taxonId, taxon]);
  if (busy) return <Busy />;
  if (!t) return <><button className="text-button" onClick={onBack}><ChevronLeft size={17} />Volver al catálogo</button>{error ? <Notice error>{error}</Notice> : <Empty title="No encontramos esta especie">Vuelve al catálogo para seleccionar una ficha disponible.</Empty>}</>;
  const occurrences = records.filter(o => o.taxonId === t.id);
  const selected = occurrences.find(o => o.id === selectedId) || occurrences[0];
  const images = [...new Set([t.image, ...occurrences.flatMap(o => o.images)].filter((u): u is string => Boolean(u)))];
  return <><button className="text-button back-link" onClick={onBack}><ChevronLeft size={17} />Volver al catálogo</button><section className="panel species-profile"><div className="profile-header"><Photo src={t.image || images[0]} name={t.scientificName} /><div><span className="eyebrow">FICHA DE ESPECIE · DARWIN CORE</span><h1 className="scientific-name">{t.scientificName}</h1><p className="profile-common-name">{t.commonName || 'Sin nombre común registrado'}</p><div className="profile-meta"><StatusBadge status={t.status} /><span><Microscope size={15} />{t.family || 'Sin familia registrada'}</span><span><MapPin size={15} />{occurrences.length} observaciones</span></div></div></div><div className="tabs profile-tabs" role="tablist" aria-label="Secciones de la ficha">{tabs.map(name => <button key={name} role="tab" id={`tab-${name}`} aria-controls="species-panel" aria-selected={name === tab} className={name === tab ? 'active' : ''} onClick={() => setTab(name)} onKeyDown={e => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); const next = tabs[(tabs.indexOf(tab) + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]; setTab(next); document.getElementById(`tab-${next}`)?.focus(); }
  }}>{name}</button>)}</div><div className="profile-content" id="species-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
    {tab === 'Taxonomía' && <div className="taxonomy-layout"><div><h2>Identificación taxonómica</h2><dl className="detail-fields">{[['Reino', t.kingdom], ['División', t.phylum], ['Clase', t.className], ['Orden', t.order], ['Familia', t.family], ['Género', t.genus], ['Especie', t.scientificName]].map(([k, v]) => <div key={k}><dt>{k}</dt><dd className={k === 'Género' || k === 'Especie' ? 'scientific-name' : ''}>{v || 'Sin dato registrado'}</dd></div>)}</dl></div><aside className="profile-note"><Microscope size={28} /><h3>Referencia taxonómica</h3><p>{t.remarks || 'No hay notas taxonómicas asociadas a esta ficha.'}</p><span className="muted">ID: {t.id}</span></aside></div>}
    {tab === 'Morfología' && <><h2>Medidas y características</h2>{occurrences.some(o => o.measurements.length) ? occurrences.map(o => o.measurements.length ? <div className="measurement-block" key={o.id}><h3>{o.locality || o.id}</h3><dl className="detail-fields">{o.measurements.map((m, i) => <div key={i}><dt>{m.name}</dt><dd>{m.value} {m.unit}</dd></div>)}</dl></div> : null) : <Empty title="Sin medidas morfológicas disponibles">El backend podrá incluir las medidas asociadas a cada ocurrencia.</Empty>}</>}
    {tab === 'Ecología' && <><h2>Contexto de las observaciones</h2>{occurrences.length ? occurrences.map(o => <article className="ecology-record" key={o.id}><div className="section-head"><h3>{o.locality || o.department || o.id}</h3><StatusBadge status={o.status} /></div><dl className="detail-fields"><div><dt>Hábitat</dt><dd>{o.habitat || 'Sin dato registrado'}</dd></div><div><dt>Sustrato</dt><dd>{o.substrate || 'Sin dato registrado'}</dd></div><div><dt>Identificado por</dt><dd>{o.author || 'Sin dato registrado'}</dd></div></dl><p>{o.remarks || 'Sin notas adicionales.'}</p>{onEdit && canEditRecord(o) && <button className="text-button" onClick={() => onEdit(o)}><Pencil size={14} />Editar observación</button>}</article>) : <Empty title="Sin contexto ecológico disponible" />}</>}
    {tab === 'Geografía' && <><h2>Distribución de las observaciones</h2>{occurrences.length ? <><OccurrenceMap records={occurrences} taxa={[t]} onSelect={o => setSelectedId(o.id)} />{selected && <div className="selected-occurrence"><strong>{selected.locality || selected.department}</strong><span>{selected.lat != null && selected.lng != null ? `${selected.lat.toFixed(5)}, ${selected.lng.toFixed(5)} · WGS84` : 'Sin coordenadas registradas'}</span><StatusBadge status={selected.status} /></div>}</> : <Empty title="Sin observaciones geográficas disponibles" />}</>}
    {tab === 'Multimedia' && <><h2>Fotografías de la especie</h2>{images.length ? <div className="detail-gallery">{images.map((src, i) => <Photo src={src} name={`${t.scientificName}, fotografía ${i + 1}`} key={src} />)}</div> : <Empty title="Aún no hay fotografías asociadas" />}{config.demo && <p className="image-disclaimer">Fotografías de referencia. Consulta la procedencia y las licencias en la guía.</p>}</>}
  </div></section></>;
}
