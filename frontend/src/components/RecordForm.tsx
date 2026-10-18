import { useState, type FormEvent } from 'react';
import type { Occurrence, PendingPhoto, Taxon, User } from '../types';
import { config } from '../lib/api';
import { validateCoordinates, validateMorphology } from '../lib/morphology.mjs';
import { Modal, Notice, Photo } from './UI';
import TaxonForm from './TaxonForm';
import { searchTaxa } from '../lib/taxon-search.mjs';
import LocationPicker from './LocationPicker';
import PhotoPicker from './PhotoPicker';
import { Fields, MeasurementEditor, MorphologyEditor, ParticipantsEditor } from './ScientificFields';

const steps = ['Hallazgo y fotos', 'Ubicación', 'Salida de campo', 'Morfología y medidas'];
const localTimestamp = (value?: string) => { if (!value) return ''; const date = new Date(value); return Number.isNaN(date.valueOf()) ? '' : new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' }).format(new Date());
export default function RecordForm({ taxa, initial, user, users, onSave, onCreateTaxon, onCancel }: { taxa: Taxon[]; initial?: Occurrence; user: User; users: User[]; onSave: (o: Occurrence, photos: PendingPhoto[]) => Promise<void>; onCreateTaxon: (taxon: Taxon) => Promise<Taxon>; onCancel: () => void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [step, setStep] = useState(0);
  const [speciesQuery, setSpeciesQuery] = useState(''); const [creatingTaxon, setCreatingTaxon] = useState(false); const [taxonBusy, setTaxonBusy] = useState(false);
  const [recordId] = useState(() => initial?.id || crypto.randomUUID());
  const [eventId] = useState(() => initial?.eventId || crypto.randomUUID());
  const [locationId] = useState(() => initial?.locationId || crypto.randomUUID());
  const [responsibleId, setResponsibleId] = useState(initial?.ownerId || user.id);
  const owners: User[] = user.role === 'admin' ? [user, ...users.filter(u => u.role === 'researcher' && u.id !== user.id)] : [user];
  if (user.role === 'admin' && initial?.ownerId && !owners.some(u => u.id === initial.ownerId)) owners.push(users.find(u => u.id === initial.ownerId) || { id: initial.ownerId, name: initial.recordedBy || initial.author || 'Responsable anterior', email: '', role: 'readonly_user' });
  const responsible = user.role === 'admin' ? owners.find(u => u.id === responsibleId) : user;
  const [photos, setPhotos] = useState<PendingPhoto[]>([]);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [morphology, setMorphology] = useState(initial?.morphology || []);
  const [measurements, setMeasurements] = useState(initial?.measurements || []);
  const [participants, setParticipants] = useState(initial?.participants || []);
  const [source, setSource] = useState<Occurrence['locationSource']>(initial?.locationSource);
  const [v, setValues] = useState({ taxonId: initial?.taxonId || '', author: initial?.author || '', date: initial?.date?.slice(0, 10) || '',
    department: initial?.department || 'Meta', municipality: initial?.municipality || '', country: initial?.country || 'CO', locality: initial?.locality || '',
    lat: initial?.lat == null ? '' : String(initial.lat), lng: initial?.lng == null ? '' : String(initial.lng),
    uncertaintyM: initial?.uncertaintyM == null ? '' : String(initial.uncertaintyM), elevationM: initial?.elevationM == null ? '' : String(initial.elevationM),
    habitat: initial?.habitat || '', substrate: initial?.substrate || '', locationRemarks: initial?.locationRemarks || '', remarks: initial?.remarks || '',
    occurrenceDate: localTimestamp(initial?.occurrenceDate), basisOfRecord: initial?.basisOfRecord || 'HumanObservation', externalOccurrenceId: initial?.externalOccurrenceId || '',
    eventType: initial?.eventType || 'Observation', fieldNumber: initial?.fieldNumber || '', eventDate: initial?.eventDate || initial?.date?.slice(0, 10) || today(),
    samplingProtocol: initial?.samplingProtocol || 'OpportunisticSearch', samplingEffort: initial?.samplingEffort || '', eventRemarks: initial?.eventRemarks || '',
  });
  const set = (key: string, value: string) => setValues(previous => ({ ...previous, [key]: value }));
  const matchingTaxa: Taxon[] = searchTaxa(taxa, speciesQuery);
  const selectedTaxon = taxa.find(t => t.id === v.taxonId);
  const availableTaxa = selectedTaxon && !matchingTaxa.some(t => t.id === selectedTaxon.id) ? [selectedTaxon, ...matchingTaxa] : matchingTaxa;
  function changeStep(next: number) { setError(''); setStep(next); document.querySelector('.modal')?.scrollTo({ top: 0, behavior: 'instant' }); }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError('');
    try {
      if (step === 1 || step === 3) { validateCoordinates(v.lat, v.lng); if (!/^[A-Za-z]{2}$/.test(v.country.trim())) throw new Error('El país debe ser un código ISO de dos letras, como CO.'); if (!v.locality.trim() || !v.department.trim()) throw new Error('Completa el departamento y la localidad.'); }
      if (!responsible) throw new Error('Selecciona el investigador responsable del hallazgo.');
      if (photoBusy) throw new Error('Espera a que termine la revisión de fotografías.');
      if (step < 3) { changeStep(step + 1); return; }
      validateMorphology(morphology);
      const seen = new Set();
      for (const m of measurements) { const key = `${m.scope || 'occurrence'}:${m.name.trim().toLowerCase()}`; if (!m.name.trim() || !m.value.trim()) throw new Error('Completa la variable y el valor de cada medida.'); if (seen.has(key)) throw new Error('No repitas una variable en el mismo ámbito de medición.'); seen.add(key); }
      const coords = validateCoordinates(v.lat, v.lng);
      setBusy(true);
      await onSave({ ...initial, ...v, ...coords, id: recordId, eventId, locationId,
        ownerId: responsible.id, recordedBy: responsible.name, locationSource: source,
        occurrenceDate: v.occurrenceDate ? new Date(v.occurrenceDate).toISOString() : '', country: v.country.trim().toUpperCase(), uncertaintyM: v.uncertaintyM === '' ? null : Number(v.uncertaintyM), elevationM: v.elevationM === '' ? null : Number(v.elevationM),
        status: 'pending', images: initial?.images || [], photos: initial?.photos || [], morphology, measurements, participants,
      }, photos);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <><form onSubmit={submit}><div className="form-stepper extended-stepper" aria-label="Pasos del registro">{steps.map((name, i) => <span key={name} className={step === i ? 'active' : step > i ? 'done' : ''} aria-current={step === i ? 'step' : undefined}><i>{i + 1}</i>{name}</span>)}</div><p className="form-intro">Paso {step + 1} de 4 · {steps[step]}. Los campos con * son obligatorios.</p>
    <fieldset hidden={step !== 0} disabled={busy || step !== 0} className="form-section"><legend className="sr-only">Hallazgo y fotografías</legend>{user.role === 'admin' ? <label className="field">Investigador responsable *<select required value={responsibleId} onChange={e => setResponsibleId(e.target.value)}>{owners.map(owner => <option key={owner.id} value={owner.id}>{owner.name}{owner.id === user.id ? ' (mi cuenta)' : ''}</option>)}</select></label> : <label className="field">Investigador responsable<input readOnly value={user.name} /><span className="field-help">Asignado automáticamente desde tu sesión.</span></label>}<label className="field">Buscar especie registrada<input type="search" value={speciesQuery} onChange={e => setSpeciesQuery(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') e.preventDefault(); }} placeholder="Nombre científico, común, género o familia" /></label><label className="field">Especie o taxón<select className="scientific-name" value={v.taxonId} onChange={e => set('taxonId', e.target.value)}><option value="">Sin identificar todavía</option>{availableTaxa.map(t => <option key={t.id} value={t.id}>{t.scientificName}{t.commonName ? ` · ${t.commonName}` : ''}</option>)}</select></label><div className="species-search-actions"><span className="muted" role="status">{matchingTaxa.length ? `${matchingTaxa.length} ${matchingTaxa.length === 1 ? 'especie encontrada' : 'especies encontradas'}` : 'No hay especies que coincidan con la búsqueda.'}</span><button type="button" className="btn small" onClick={() => setCreatingTaxon(true)}>Añadir especie nueva</button></div><Fields value={v} onChange={set} fields={[
      { key: 'basisOfRecord', label: 'Tipo de registro', required: true, options: [['HumanObservation', 'Observación humana'], ['PreservedSpecimen', 'Espécimen preservado'], ['MaterialSample', 'Muestra de material'], ['LivingSpecimen', 'Espécimen vivo']] },
      { key: 'externalOccurrenceId', label: 'Identificador externo del hallazgo' }, { key: 'occurrenceDate', label: 'Fecha y hora del hallazgo (opcional)', type: 'datetime-local' }, { key: 'author', label: 'Identificado por' }, { key: 'date', label: 'Fecha de identificación', type: 'date' },
      { key: 'substrate', label: 'Sustrato', max: 40 }, { key: 'remarks', label: 'Notas del hallazgo', type: 'textarea' },
    ]} /><h3>Fotografías del hallazgo</h3><p className="muted">Puedes subir fotos ahora y añadir más después desde este registro o su ficha de especie.</p>{!!initial?.images.length && <div className="existing-photos">{initial.images.map((src, i) => <Photo key={`${src}-${i}`} src={src} name={`Fotografía guardada ${i + 1}`} />)}</div>}<PhotoPicker value={photos} onChange={setPhotos} photographer={user.name} onBusyChange={setPhotoBusy} /></fieldset>
    <fieldset hidden={step !== 1} disabled={busy || step !== 1} className="form-section"><legend className="sr-only">Ubicación</legend><LocationPicker active={step === 1} lat={v.lat} lng={v.lng} onChange={point => { setSource(point.source); setValues(previous => ({ ...previous, lat: point.lat, lng: point.lng, uncertaintyM: point.uncertaintyM ?? previous.uncertaintyM, elevationM: point.elevationM ?? previous.elevationM })); }} /><Fields value={v} onChange={set} fields={[
      { key: 'country', label: 'País (código ISO de 2 letras)', required: true, max: 2 }, { key: 'department', label: 'Departamento', required: true }, { key: 'municipality', label: 'Municipio' },
      { key: 'locality', label: 'Localidad o descripción del sitio', required: true }, { key: 'habitat', label: 'Hábitat', max: 40 },
      { key: 'uncertaintyM', label: 'Incertidumbre de coordenadas (m)', type: 'number', min: 0, max: 99999999.99 }, { key: 'elevationM', label: 'Elevación (m)', type: 'number', min: -99999.99, max: 99999.99 },
      { key: 'locationRemarks', label: 'Notas de la ubicación', type: 'textarea' },
    ]} /></fieldset>
    <fieldset hidden={step !== 2} disabled={busy || step !== 2} className="form-section"><legend className="sr-only">Salida de campo</legend><label className="field">Registrado por<input readOnly value={responsible?.name || ''} /><span className="field-help">Investigador responsable de este hallazgo.</span></label><Fields value={v} onChange={set} fields={[
      { key: 'eventDate', label: 'Fecha de observación / salida', type: 'date', required: true },
      { key: 'eventType', label: 'Tipo de evento', options: [['Observation', 'Observación'], ['Survey', 'Muestreo'], ['Expedition', 'Expedición'], ['SiteVisit', 'Visita al sitio'], ['SamplingEvent', 'Evento de muestreo']] },
      { key: 'fieldNumber', label: 'Código de campo', max: 32 }, { key: 'samplingProtocol', label: 'Protocolo', options: [['', 'Sin especificar'], ['OpportunisticSearch', 'Búsqueda oportunista'], ['LinearTransect', 'Transecto lineal'], ['FixedPlot', 'Parcela fija']] },
      { key: 'samplingEffort', label: 'Esfuerzo de muestreo', max: 32 }, { key: 'eventRemarks', label: 'Notas de la salida', type: 'textarea' },
    ]} /><h3>Participantes y créditos</h3><ParticipantsEditor value={participants} onChange={setParticipants} /></fieldset>
    <fieldset hidden={step !== 3} disabled={busy || step !== 3} className="form-section"><legend className="sr-only">Morfología y medidas</legend><h3>Morfología de este espécimen</h3><MorphologyEditor value={morphology} onChange={setMorphology} /><h3 className="form-subheading">Microclima y otras medidas</h3><MeasurementEditor value={measurements} onChange={setMeasurements} /><div className="record-summary"><strong>Antes de guardar</strong><p>Investigador responsable: {responsible?.name}</p>{user.role === 'admin' && responsibleId !== user.id && <p>Registras este hallazgo a nombre de otra cuenta investigadora.</p>}<p><em>{taxa.find(t => t.id === v.taxonId)?.scientificName || 'Sin identificar'}</em> · {v.locality || 'Sin localidad'} · {v.eventDate}</p><p>{(initial?.images.length || 0) + photos.length} fotografías · {morphology.length} rasgos · {measurements.length} medidas</p></div>{config.demo && <Notice>Se guardará en este navegador como registro en revisión.</Notice>}</fieldset>
    {error && <Notice error>{error}</Notice>}<div className="form-actions"><button className="btn" type="button" disabled={busy} onClick={step === 0 ? onCancel : () => changeStep(step - 1)}>{step === 0 ? 'Cancelar' : 'Anterior'}</button><button className="btn primary" disabled={busy || photoBusy}>{busy ? 'Guardando…' : step < 3 ? 'Continuar' : initial ? 'Guardar cambios' : 'Guardar registro'}</button></div>
  </form>{creatingTaxon && <Modal title="Añadir especie nueva al catálogo" wide onClose={() => { if (!taxonBusy) setCreatingTaxon(false); }}><TaxonForm existing={taxa} ownerId={user.id} onCancel={() => setCreatingTaxon(false)} onSave={async taxon => {
    setTaxonBusy(true);
    try { const saved = await onCreateTaxon(taxon); set('taxonId', saved.id); setSpeciesQuery(saved.scientificName); setCreatingTaxon(false); }
    finally { setTaxonBusy(false); }
  }} /></Modal>}</>;
}

