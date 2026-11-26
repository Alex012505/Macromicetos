import { useMemo, useState, type FormEvent } from 'react';
import { Pencil, Plus, Search, Trash2 } from 'lucide-react';
import type { Dataset, EthnoSurvey, EthnoUse, Taxon, User } from '../types';
import { Empty, Modal, Notice } from './UI';
import { Fields, type FieldSpec } from './ScientificFields';

const ANONYMITY: Record<string, string> = { anonymous: 'Anónimo', pseudonym: 'Seudónimo', identified: 'Identificado' };
const USE_CATEGORY: Record<string, string> = {
  edible: 'Comestible', medicinal: 'Medicinal', ritual: 'Ritual', dye: 'Tinte',
  soil_improvement: 'Mejora del suelo', biological_control: 'Control biológico',
  animal_feed: 'Alimento animal', other: 'Otro',
};

const SOURCE_FIELDS: FieldSpec[] = [
  { key: 'interviewDate', label: 'Fecha de entrevista', type: 'date', required: true },
  { key: 'interviewer', label: 'Entrevistador/a', required: true },
  { key: 'consentType', label: 'Tipo de consentimiento', options: [['', 'Sin especificar'], ['verbal', 'Verbal'], ['written', 'Escrito']] },
  { key: 'anonymityLevel', label: 'Anonimato', options: [['anonymous', 'Anónimo'], ['pseudonym', 'Seudónimo'], ['identified', 'Identificado']] },
  { key: 'ageRange', label: 'Rango de edad', options: [['', 'Sin especificar'], ['12-17', '12–17'], ['18-25', '18–25'], ['26-40', '26–40'], ['41-60', '41–60'], ['60+', '60+']] },
  { key: 'gender', label: 'Género (persona)', options: [['', 'Sin especificar'], ['male', 'Masculino'], ['female', 'Femenino'], ['non_binary', 'No binario'], ['prefer_not_to_say', 'Prefiere no decirlo']] },
  { key: 'occupation', label: 'Ocupación', options: [['', 'Sin especificar'], ['farmer', 'Agricultor/a'], ['fisher', 'Pescador/a'], ['indigenous_knowledge_holder', 'Sabedor/a indígena'], ['rancher', 'Ganadero/a'], ['forester', 'Silvicultor/a'], ['student', 'Estudiante'], ['teacher', 'Docente'], ['other', 'Otra']] },
  { key: 'stateProvince', label: 'Departamento' },
  { key: 'municipality', label: 'Municipio' },
  { key: 'village', label: 'Vereda' },
  { key: 'remarks', label: 'Notas de la entrevista', type: 'textarea' },
];

const KNOWLEDGE_FIELDS: FieldSpec[] = [
  { key: 'localName', label: 'Nombre local del hongo' },
  { key: 'learningSource', label: 'Origen del conocimiento', options: [['', 'Sin especificar'], ['family', 'Familia'], ['community', 'Comunidad'], ['personal_experience', 'Experiencia personal'], ['books', 'Libros'], ['workshops', 'Talleres'], ['internet', 'Internet'], ['other', 'Otra']] },
  { key: 'recognitionCues', label: 'Criterios de reconocimiento', type: 'textarea' },
  { key: 'foundInPlaces', label: 'Lugares donde se encuentra' },
  { key: 'seasonality', label: 'Estacionalidad' },
  { key: 'months', label: 'Meses de presencia', max: 64 },
  { key: 'safetyPractices', label: 'Prácticas de seguridad', type: 'textarea' },
  { key: 'mythsStories', label: 'Relatos y mitos', type: 'textarea' },
  { key: 'culturalIdentity', label: 'Identidad cultural', options: [['', 'Sin especificar'], ['yes', 'Sí'], ['no', 'No'], ['partial', 'Parcial']] },
  { key: 'recommendations', label: 'Recomendaciones de la fuente', type: 'textarea' },
];

const USE_FIELDS: FieldSpec[] = [
  { key: 'useCategory', label: 'Categoría de uso', required: true, options: [['', 'Selecciona una categoría'], ['edible', 'Comestible'], ['medicinal', 'Medicinal'], ['ritual', 'Ritual'], ['dye', 'Tinte'], ['soil_improvement', 'Mejora del suelo'], ['biological_control', 'Control biológico'], ['animal_feed', 'Alimento animal'], ['other', 'Otro']] },
  { key: 'importance', label: 'Importancia', options: [['', 'Sin especificar'], ['high', 'Alta'], ['medium', 'Media'], ['low', 'Baja']] },
  { key: 'preparationMethod', label: 'Preparación', type: 'textarea' },
  { key: 'ailment', label: 'Afección mencionada' },
  { key: 'dosage', label: 'Dosificación reportada' },
  { key: 'contraindications', label: 'Contraindicaciones reportadas', type: 'textarea' },
];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function blankSurvey(user: User): EthnoSurvey {
  return {
    id: crypto.randomUUID(), interviewDate: today(), interviewer: user.name || '',
    consentGiven: false, anonymityLevel: 'anonymous', knowsFungi: true, uses: [],
  };
}

function dateLabel(value: string) {
  if (!value) return 'Sin fecha';
  const date = new Date(`${value.slice(0, 10)}T12:00:00`);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat('es-CO', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'America/Bogota',
  }).format(date);
}

export default function Interviews({ data, user, onSave, onDelete }: {
  data: Dataset;
  user: User;
  onSave: (taxonId: string, survey: EthnoSurvey) => Promise<EthnoSurvey>;
  onDelete: (taxonId: string, survey: EthnoSurvey) => Promise<void>;
}) {
  const canWrite = user.role === 'analyst' || user.role === 'admin';
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState<EthnoSurvey | null>(null);
  const [taxonId, setTaxonId] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const canEditTaxon = (taxon: Taxon) => user.role === 'admin'
    || (user.role === 'analyst' && Boolean(user.id) && taxon.ownerId === user.id);
  const selectable = useMemo(() => data.taxa.filter(canEditTaxon).sort((a, b) => a.scientificName.localeCompare(b.scientificName)), [data.taxa, user]);
  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return data.taxa.flatMap(taxon => (taxon.knowledge || []).map(survey => ({ taxon, survey })))
      .filter(({ taxon, survey }) => !needle || [taxon.scientificName, taxon.commonName, survey.interviewer,
        survey.localName, survey.municipality, survey.village].some(value => String(value || '').toLowerCase().includes(needle)))
      .sort((a, b) => (b.survey.interviewDate || '').localeCompare(a.survey.interviewDate || ''));
  }, [data.taxa, query]);

  function openNew() {
    setError('');
    if (!selectable.length) { setError('No tienes fichas de especie asignadas. Un administrador debe asignarte una ficha antes de registrar entrevistas.'); return; }
    setTaxonId(selectable[0].id);
    setEditing(blankSurvey(user));
  }

  function openEdit(taxon: Taxon, survey: EthnoSurvey) {
    setError('');
    setTaxonId(taxon.id);
    setEditing({ ...survey, taxonId: taxon.id, uses: survey.uses.map(use => ({ ...use })) });
  }

  function updateSurvey(patch: Partial<EthnoSurvey>) {
    setEditing(current => current ? { ...current, ...patch } : current);
  }

  function updateUse(id: string, key: string, value: unknown) {
    setEditing(current => current ? {
      ...current,
      uses: current.uses.map(use => use.id === id ? { ...use, [key]: value } as EthnoUse : use),
    } : current);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    setError('');
    try {
      if (!taxonId) throw new Error('Selecciona la especie asociada a la entrevista.');
      if (!editing.interviewDate) throw new Error('Indica la fecha de la entrevista.');
      if (!editing.interviewer.trim()) throw new Error('Registra el nombre del entrevistador o entrevistadora.');
      if (!editing.consentGiven) throw new Error('Para guardar una entrevista es necesario registrar el consentimiento otorgado.');
      if (editing.uses.some(use => !use.useCategory)) throw new Error('Cada uso reportado necesita una categoría.');
      setBusy(true);
      await onSave(taxonId, { ...editing, taxonId });
      setEditing(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(taxon: Taxon, survey: EthnoSurvey) {
    if (!survey.knowledgeId) return;
    if (!window.confirm(`¿Retirar la entrevista de ${taxon.scientificName} del ${dateLabel(survey.interviewDate)}?`)) return;
    setError('');
    setBusy(true);
    try { await onDelete(taxon.id, survey); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading">
      <div>
        <span className="eyebrow">CONOCIMIENTO SOCIOECOLÓGICO</span>
        <h1>Entrevistas y saberes<span className="heading-dot">.</span></h1>
        <p>Documenta el conocimiento local asociado a cada especie: fuente, reconocimiento, prácticas y usos reportados.</p>
      </div>
      {canWrite && <button className="btn primary" onClick={openNew} disabled={!selectable.length}><Plus size={18} />Nueva entrevista</button>}
    </div>

    <div className="filter-bar">
      <label className="search-input"><Search size={18} /><input aria-label="Buscar entrevistas" placeholder="Buscar por especie, entrevistador/a, nombre local o lugar…" value={query} onChange={e => setQuery(e.target.value)} /></label>
      <span className="muted">{rows.length} {rows.length === 1 ? 'entrevista' : 'entrevistas'}</span>
    </div>

    {error && !editing && <Notice error>{error}</Notice>}
    {!canWrite && <p className="muted">Puedes consultar las entrevistas; para editarlas se requiere el perfil de investigador responsable de la ficha.</p>}

    {rows.length ? <div className="interview-grid">{rows.map(({ taxon, survey }) => <article className="panel interview-card" key={survey.knowledgeId || `${taxon.id}-${survey.id}`}>
      <header>
        <div>
          <span className="eyebrow">{dateLabel(survey.interviewDate)}</span>
          <h2 className="scientific-name">{taxon.scientificName}</h2>
          <p>{taxon.commonName || 'Sin nombre común'}</p>
        </div>
        {canWrite && canEditTaxon(taxon) && <div className="form-actions start">
          <button className="text-button" type="button" onClick={() => openEdit(taxon, survey)}><Pencil size={14} />Editar</button>
          <button className="text-button danger" type="button" onClick={() => void remove(taxon, survey)} disabled={busy}><Trash2 size={14} />Eliminar</button>
        </div>}
      </header>
      <dl className="detail-fields">
        <div><dt>Entrevistador/a</dt><dd>{survey.interviewer || 'Sin dato'}</dd></div>
        <div><dt>Anonimato</dt><dd>{ANONYMITY[survey.anonymityLevel] || 'Sin dato'}</dd></div>
        <div><dt>Nombre local</dt><dd>{survey.localName || 'Sin dato'}</dd></div>
        <div><dt>Lugar</dt><dd>{[survey.municipality, survey.village].filter(Boolean).join(' · ') || 'Sin dato'}</dd></div>
        <div><dt>Usos reportados</dt><dd>{survey.uses.length ? survey.uses.map(use => USE_CATEGORY[use.useCategory] || use.useCategory).join(', ') : 'Sin usos reportados'}</dd></div>
      </dl>
    </article>)}</div> : <Empty title="Aún no hay entrevistas registradas">Las entrevistas aparecerán aquí asociadas a su especie. {canWrite && selectable.length ? 'Usa «Nueva entrevista» para comenzar.' : ''}</Empty>}

    {editing && <Modal title={editing.knowledgeId ? 'Editar entrevista' : 'Nueva entrevista'} wide onClose={() => { if (!busy) setEditing(null); }}>
      <form onSubmit={submit}>
        <p className="form-intro">La entrevista se asocia a una especie del catálogo. Los datos de la persona entrevistada se guardan de forma anónima o seudónima; no se publican en las descargas.</p>
        <fieldset disabled={busy} className="form-section">
          {editing.knowledgeId
            ? <p className="field-static"><strong>Especie:</strong> <span className="scientific-name">{data.taxa.find(t => t.id === taxonId)?.scientificName || 'Sin identificación'}</span></p>
            : <label className="field">Especie asociada *<select value={taxonId} onChange={e => setTaxonId(e.target.value)} required><option value="">Selecciona una especie</option>{selectable.map(taxon => <option key={taxon.id} value={taxon.id}>{taxon.scientificName}{taxon.commonName ? ` · ${taxon.commonName}` : ''}</option>)}</select></label>}

          <h3>Datos de la entrevista</h3>
          <Fields fields={SOURCE_FIELDS} value={editing} onChange={(key, value) => updateSurvey({ [key]: value })} />
          <label className="checkbox-label"><input type="checkbox" checked={editing.consentGiven} onChange={e => updateSurvey({ consentGiven: e.target.checked })} />Consentimiento otorgado *</label>

          <h3>Conocimiento sobre la especie</h3>
          <label className="checkbox-label"><input type="checkbox" checked={editing.knowsFungi} onChange={e => updateSurvey({ knowsFungi: e.target.checked })} />La persona conoce los hongos</label>
          <Fields fields={KNOWLEDGE_FIELDS} value={editing} onChange={(key, value) => updateSurvey({ [key]: value })} />

          <h3>Usos reportados</h3>
          {editing.uses.map((use, index) => <fieldset className="entry-card" key={use.id}>
            <legend>Uso reportado {index + 1}</legend>
            <Fields fields={USE_FIELDS} value={use} onChange={(key, value) => updateUse(use.id, key, value)} />
            <label className="checkbox-label"><input type="checkbox" checked={use.usesFungi !== false} onChange={e => updateUse(use.id, 'usesFungi', e.target.checked)} />La fuente reporta uso de este hongo</label>
            <button type="button" className="text-button danger" onClick={() => updateSurvey({ uses: editing.uses.filter(item => item.id !== use.id) })}>Quitar uso</button>
          </fieldset>)}
          <button type="button" className="btn small" onClick={() => updateSurvey({ uses: [...editing.uses, { id: crypto.randomUUID(), useCategory: '', usesFungi: true }] })}>Añadir uso reportado</button>
        </fieldset>
        {error && <Notice error>{error}</Notice>}
        <div className="form-actions">
          <button className="btn" type="button" onClick={() => setEditing(null)} disabled={busy}>Cancelar</button>
          <button className="btn primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar entrevista'}</button>
        </div>
      </form>
    </Modal>}
  </>;
}
