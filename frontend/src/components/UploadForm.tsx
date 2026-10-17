import { useState, type FormEvent } from 'react';
import type { Occurrence, PendingPhoto, Taxon } from '../types';
import PhotoPicker from './PhotoPicker';
import { Notice } from './UI';

export default function UploadForm({ records, taxa, initialId = '', photographer, onDone }: { records: Occurrence[]; taxa: Taxon[]; initialId?: string; photographer: string; onDone: (id: string, photos: PendingPhoto[]) => Promise<void> }) {
  const [id, setId] = useState(initialId); const [photos, setPhotos] = useState<PendingPhoto[]>([]); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [photoBusy, setPhotoBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault(); setError('');
    if (!photos.length) { setError('Selecciona al menos una fotografía.'); return; }
    setBusy(true);
    try { await onDone(id, photos); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <form onSubmit={submit}><p className="form-intro">Añade fotografías al mismo hallazgo, conservando sus créditos y el tipo de vista.</p><fieldset disabled={busy} className="form-section"><label className="field">Hallazgo *<select name="recordId" required value={id} onChange={e => setId(e.target.value)} className="scientific-name"><option value="">Selecciona un registro</option>{records.map(o => <option key={o.id} value={o.id}>{taxa.find(t => t.id === o.taxonId)?.scientificName || 'Sin identificar'} · {o.locality || o.department} · {(o.eventDate || o.date).slice(0, 10)} · {o.id.slice(0, 8)}</option>)}</select></label><PhotoPicker value={photos} onChange={setPhotos} photographer={photographer} onBusyChange={setPhotoBusy} /></fieldset>{!records.length && <Notice>Primero crea un hallazgo para asociar sus fotos.</Notice>}{error && <Notice error>{error}</Notice>}<button className="btn primary full-width" disabled={busy || photoBusy || !records.length}>{busy ? 'Guardando fotografías…' : 'Añadir fotografías'}</button></form>;
}

