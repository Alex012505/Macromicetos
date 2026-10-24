import type { Measurement, MorphologyFact, Participant, ScientificSource, EthnoSurvey, EthnoUse } from '../types';
import { morphologyTypes } from '../lib/morphology.mjs';

export interface FieldSpec { key: string; label: string; type?: string; required?: boolean; max?: number; min?: number; options?: string[][]; scientific?: boolean; step?: string }
export function Fields({ fields, value, onChange }: { fields: FieldSpec[]; value: object; onChange: (key: string, value: string) => void }) {
  return <div className="form-grid">{fields.map(f => {
    const v = String((value as Record<string, unknown>)[f.key] ?? '');
    const props = { value: v, 'aria-label': f.label, onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => onChange(f.key, e.target.value), required: f.required, className: f.scientific ? 'scientific-name' : undefined };
    return <label className={`field ${f.type === 'textarea' ? 'span-2' : ''}`} key={f.key}>{f.label}{f.required ? ' *' : ''}{f.options ? <select {...props}>{f.options.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select> : f.type === 'textarea' ? <textarea {...props} rows={3} maxLength={f.max || 4000} /> : <input {...props} type={f.type || 'text'} min={f.min} max={f.type === 'number' ? f.max : undefined} step={f.type === 'number' ? f.step || 'any' : undefined} maxLength={f.type !== 'number' ? f.max || 300 : undefined} />}</label>;
  })}</div>;
}
export function MorphologyEditor({ value, onChange }: { value: MorphologyFact[]; onChange: (v: MorphologyFact[]) => void }) {
  const update = (i: number, key: string, v: string) => onChange(value.map((m, j) => j === i ? { ...m, [key]: v } : m));
  return <div className="repeating-fields"><p className="muted">Registra únicamente los rasgos observados. Cada rasgo se admite una vez; los rangos como 5–8 se conservan como texto.</p>{value.map((m, i) => <fieldset className="entry-card" key={i}><legend>Rasgo {i + 1}</legend><Fields fields={[
    { key: 'type', label: 'Rasgo', required: true, options: morphologyTypes.filter(([key]) => key === m.type || !value.some(v => v.type === key)) },
    { key: 'value', label: 'Valor o descripción', required: true },
    { key: 'unit', label: 'Unidad', options: [['', 'Sin unidad (descripción)'], ['cm', 'cm'], ['mm', 'mm']] },
    { key: 'determinedDate', label: 'Fecha de evaluación', type: 'date' }, { key: 'remarks', label: 'Notas del rasgo', type: 'textarea' },
  ]} value={m} onChange={(key, v) => update(i, key, v)} /><button className="text-button danger" type="button" onClick={() => onChange(value.filter((_, j) => i !== j))}>Quitar rasgo {i + 1}</button></fieldset>)}<button type="button" className="btn small" disabled={value.length >= morphologyTypes.length} onClick={() => onChange([...value, { type: morphologyTypes.find(([type]) => !value.some(m => m.type === type))![0], value: '', unit: '' }])}>Añadir rasgo morfológico</button></div>;
}
export function MeasurementEditor({ value, onChange }: { value: Measurement[]; onChange: (v: Measurement[]) => void }) {
  return <div className="repeating-fields"><p className="muted">Microclima y otras medidas: temperatura, humedad, pH o dimensiones adicionales. Indica si corresponden a la salida o al espécimen.</p>{value.map((m, i) => <fieldset className="entry-card" key={i}><legend>Medida {i + 1}</legend><Fields value={m} fields={[
    { key: 'name', label: 'Variable', required: true, max: 40 }, { key: 'value', label: 'Valor', required: true }, { key: 'unit', label: 'Unidad', max: 24 },
    { key: 'scope', label: 'Corresponde a', options: [['occurrence', 'Este hallazgo'], ['event', 'La salida de campo']] },
  ]} onChange={(key, v) => onChange(value.map((r, j) => i === j ? { ...r, [key]: v } : r))} /><button type="button" className="text-button danger" onClick={() => onChange(value.filter((_, j) => j !== i))}>Quitar medida {i + 1}</button></fieldset>)}<button type="button" className="btn small" onClick={() => onChange([...value, { name: '', value: '', unit: '', scope: 'occurrence' }])}>Añadir medida ambiental</button></div>;
}
export function ParticipantsEditor({ value, onChange, taxon = false, media = false }: { value: Participant[]; onChange: (v: Participant[]) => void; taxon?: boolean; media?: boolean }) {
  return <>{value.map((p, i) => <fieldset className="entry-card" key={p.id}><legend>Participante {i + 1}</legend><Fields value={p} fields={[
    { key: 'givenName', label: 'Nombres', required: true }, { key: 'familyName', label: 'Apellidos' },
    { key: 'displayName', label: 'Nombre para créditos', required: true }, { key: 'orcid', label: 'ORCID', max: 19 },
    { key: 'affiliation', label: 'Afiliación' }, { key: 'contactEmail', label: 'Correo de contacto', type: 'email', max: 254 },
    ...(media ? [{ key: 'role', label: 'Crédito', options: [['photographer', 'Fotógrafo/a'], ['rights_holder', 'Titular de derechos'], ['creator', 'Creador/a'], ['provider', 'Proveedor/a']] }] : !taxon ? [{ key: 'role', label: 'Función', options: [['observer', 'Observador/a'], ['photographer', 'Fotógrafo/a'], ['collector', 'Recolector/a'], ['identifier', 'Identificador/a'], ['coordinator', 'Coordinador/a']] }, { key: 'scope', label: 'Participación en', options: [['occurrence', 'Este hallazgo'], ['event', 'La salida de campo']] }] : []),
  ]} onChange={(key, v) => onChange(value.map((r, j) => i === j ? { ...r, [key]: v } : r))} />{!taxon && (media || p.scope === 'event') && <label className="checkbox-label"><input type="checkbox" checked={!!p.isPrimary} onChange={e => onChange(value.map((r, j) => i === j ? { ...r, isPrimary: e.target.checked } : r))} />{media ? 'Crédito principal' : 'Participante principal de la salida'}</label>}<button type="button" className="text-button danger" onClick={() => onChange(value.filter(r => r.id !== p.id))}>Quitar participante</button></fieldset>)}<button type="button" className="btn small" onClick={() => onChange([...value, { id: crypto.randomUUID(), givenName: '', displayName: '', role: media ? 'photographer' : 'observer', scope: 'occurrence' }])}>Añadir {media ? 'persona acreditada' : taxon ? 'responsable taxonómico' : 'participante'}</button></>;
}
export function SourcesEditor({ value, onChange }: { value: ScientificSource[]; onChange: (v: ScientificSource[]) => void }) {
  return <>{value.map((s, i) => <fieldset className="entry-card" key={s.id}><legend>Referencia {i + 1}</legend><Fields value={s} fields={[
    { key: 'sourceType', label: 'Tipo de fuente', required: true, options: [['article', 'Artículo'], ['book', 'Libro'], ['thesis', 'Tesis'], ['report', 'Informe'], ['website', 'Sitio web'], ['other', 'Otra']] },
    { key: 'title', label: 'Título', required: true }, { key: 'authors', label: 'Autores' }, { key: 'year', label: 'Año', type: 'number', min: 1, max: 32767, step: '1' }, { key: 'doi', label: 'DOI', max: 120 },
  ]} onChange={(key, v) => onChange(value.map(r => r.id === s.id ? { ...r, [key]: v } : r))} /><button type="button" className="text-button danger" onClick={() => onChange(value.filter(r => r.id !== s.id))}>Quitar referencia</button></fieldset>)}<button type="button" className="btn small" onClick={() => onChange([...value, { id: crypto.randomUUID(), sourceType: 'article', title: '' }])}>Añadir referencia</button></>;
}
export function KnowledgeEditor({ value, onChange }: { value: EthnoSurvey[]; onChange: (v: EthnoSurvey[]) => void }) {
  const update = (id: string, patch: Partial<EthnoSurvey>) => onChange(value.map(s => s.id === id ? { ...s, ...patch } : s));
  return <><p className="muted">Documenta lo expresado en la entrevista y su consentimiento. Estos datos no se incluyen en las exportaciones públicas ni en la ficha descargable.</p>{value.map((s, i) => <fieldset className="entry-card" key={s.id}><legend>Entrevista {i + 1}</legend><Fields value={s} fields={[
    { key: 'interviewDate', label: 'Fecha de entrevista', type: 'date', required: true }, { key: 'interviewer', label: 'Entrevistador/a', required: true },
    { key: 'consentType', label: 'Tipo de consentimiento', max: 12, options: [['', 'Sin especificar'], ['verbal', 'Verbal'], ['written', 'Escrito']] },
    { key: 'anonymityLevel', label: 'Anonimato', options: [['anonymous', 'Anónimo'], ['pseudonym', 'Seudónimo'], ['identified', 'Identificado']] },
    { key: 'ageRange', label: 'Rango de edad', max: 10 }, { key: 'gender', label: 'Género (persona)', max: 20 }, { key: 'occupation', label: 'Ocupación', max: 32 },
    { key: 'stateProvince', label: 'Departamento' }, { key: 'municipality', label: 'Municipio' }, { key: 'village', label: 'Vereda' },
    { key: 'localName', label: 'Nombre local del hongo' }, { key: 'learningSource', label: 'Origen del conocimiento', max: 32 },
    { key: 'recognitionCues', label: 'Criterios de reconocimiento', type: 'textarea' }, { key: 'foundInPlaces', label: 'Lugares donde se encuentra' },
    { key: 'seasonality', label: 'Estacionalidad' }, { key: 'months', label: 'Meses de presencia', max: 64 }, { key: 'safetyPractices', label: 'Prácticas de seguridad', type: 'textarea' },
    { key: 'mythsStories', label: 'Relatos y mitos', type: 'textarea' }, { key: 'culturalIdentity', label: 'Identidad cultural', max: 16 }, { key: 'remarks', label: 'Notas de entrevista', type: 'textarea' },
  ]} onChange={(key, v) => update(s.id, { [key]: v })} /><label className="checkbox-label"><input type="checkbox" checked={s.consentGiven} onChange={e => update(s.id, { consentGiven: e.target.checked })} />Consentimiento otorgado</label><label className="checkbox-label"><input type="checkbox" checked={s.knowsFungi} onChange={e => update(s.id, { knowsFungi: e.target.checked })} />La persona conoce los hongos</label>
    {s.uses.map((u, j) => <fieldset className="entry-card" key={u.id}><legend>Uso reportado {j + 1}</legend><Fields value={u} fields={[
      { key: 'useCategory', label: 'Categoría de uso', required: true, max: 32 }, { key: 'importance', label: 'Importancia', max: 10 }, { key: 'preparationMethod', label: 'Preparación', type: 'textarea' },
      { key: 'ailment', label: 'Afección mencionada' }, { key: 'dosage', label: 'Dosificación reportada' }, { key: 'contraindications', label: 'Contraindicaciones reportadas', type: 'textarea' }, { key: 'recommendations', label: 'Recomendaciones de la fuente', type: 'textarea' },
    ]} onChange={(key, v) => update(s.id, { uses: s.uses.map(r => r.id === u.id ? { ...r, [key]: v } as EthnoUse : r) })} /><button type="button" className="text-button danger" onClick={() => update(s.id, { uses: s.uses.filter(r => r.id !== u.id) })}>Quitar uso</button></fieldset>)}
    <div className="form-actions start"><button type="button" className="btn small" onClick={() => update(s.id, { uses: [...s.uses, { id: crypto.randomUUID(), useCategory: '' }] })}>Añadir uso reportado</button><button type="button" className="text-button danger" onClick={() => onChange(value.filter(r => r.id !== s.id))}>Quitar entrevista</button></div>
  </fieldset>)}<button type="button" className="btn small" onClick={() => onChange([...value, { id: crypto.randomUUID(), interviewDate: '', interviewer: '', consentGiven: false, anonymityLevel: 'anonymous', knowsFungi: true, uses: [] }])}>Añadir entrevista</button></>;
}
