import { useState, type FormEvent } from 'react';
import type { Taxon } from '../types';
import { validateMorphology } from '../lib/morphology.mjs';
import { Fields, KnowledgeEditor, MorphologyEditor, ParticipantsEditor, SourcesEditor } from './ScientificFields';
import { Notice } from './UI';

export default function TaxonForm({ existing, initial, ownerId, onSave, onCancel }: { existing: Taxon[]; initial?: Taxon; ownerId: string; onSave: (taxon: Taxon) => Promise<void>; onCancel: () => void }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [v, setValues] = useState<Taxon>(() => initial || { id: crypto.randomUUID(), ownerId, scientificName: '', commonName: '', kingdom: 'Fungi', phylum: '', className: '', order: '', family: '', genus: '', specificEpithet: '', externalTaxonId: '', rank: 'species', remarks: '', status: 'pending' });
  const set = (key: string, value: unknown) => setValues(previous => ({ ...previous, [key]: value }));
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError('');
    try {
      const name = v.scientificName.trim().replace(/\s+/g, ' '), rank = v.rank || 'species';
      if (['species', 'subspecies', 'variety'].includes(rank) && name.split(/\s+/).length < 2) throw new Error('Escribe al menos el género y el epíteto para este rango.');
      if (!name || !v.kingdom.trim()) throw new Error('Completa el nombre científico y el reino.');
      if (v.sources?.some(s => s.year && !Number.isInteger(Number(s.year)))) throw new Error('El año bibliográfico debe ser un número entero.');
      if (existing.some(t => t.id !== v.id && t.scientificName.toLowerCase() === name.toLowerCase() && (t.rank || 'species') === rank)) throw new Error('Este nombre y rango ya existen en el catálogo.');
      validateMorphology(v.morphology);
      if (v.knowledge?.some(s => !s.consentGiven)) throw new Error('Para guardar una entrevista es necesario registrar el consentimiento otorgado. Si no lo tienes, retira esa entrevista.');
      setBusy(true); await onSave({ ...v, rank, scientificName: name, genus: v.genus.trim() || name.split(' ')[0], specificEpithet: v.specificEpithet || (rank === 'species' ? name.split(' ')[1] : ''), status: 'pending' });
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <form onSubmit={submit}><p className="form-intro">Completa la taxonomía y añade la información disponible. Los rasgos generales de la especie se guardan separados de las mediciones de los hallazgos.</p><fieldset disabled={busy} className="form-section"><Fields value={v} onChange={set} fields={[
    { key: 'scientificName', label: 'Nombre científico', required: true, scientific: true }, { key: 'commonName', label: 'Nombre común' },
    { key: 'rank', label: 'Rango taxonómico', required: true, options: [['species', 'Especie'], ['genus', 'Género'], ['subspecies', 'Subespecie'], ['variety', 'Variedad']] },
    { key: 'kingdom', label: 'Reino', required: true }, { key: 'phylum', label: 'División' }, { key: 'className', label: 'Clase' }, { key: 'order', label: 'Orden' }, { key: 'family', label: 'Familia' },
    { key: 'genus', label: 'Género', scientific: true }, { key: 'specificEpithet', label: 'Epíteto específico', scientific: true }, { key: 'externalTaxonId', label: 'Identificador taxonómico externo', max: 40 },
    { key: 'remarks', label: 'Notas taxonómicas', type: 'textarea' },
  ]} /><section className="editor-section"><h3>Morfología general de la especie</h3><MorphologyEditor value={v.morphology || []} onChange={items => set('morphology', items)} /></section><section className="editor-section"><h3>Fuentes bibliográficas</h3><SourcesEditor value={v.sources || []} onChange={items => set('sources', items)} /></section><section className="editor-section"><h3>Responsables de la ficha</h3><ParticipantsEditor taxon value={v.participants || []} onChange={items => set('participants', items)} /></section><section className="editor-section"><h3>Conocimiento socioecológico</h3><KnowledgeEditor value={v.knowledge || []} onChange={items => set('knowledge', items)} /></section></fieldset>{error && <Notice error>{error}</Notice>}<div className="form-actions"><button className="btn" type="button" onClick={onCancel} disabled={busy}>Cancelar</button><button className="btn primary" disabled={busy}>{busy ? 'Guardando…' : initial ? 'Guardar ficha' : 'Añadir especie'}</button></div></form>;
}
