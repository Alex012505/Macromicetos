import { useEffect, useRef, useState } from 'react';
import type { PendingPhoto } from '../types';
import { config } from '../lib/api';
import { Fields, ParticipantsEditor } from './ScientificFields';
import { Notice } from './UI';

export const photoTypes = [['habitus', 'Vista general'], ['pileus', 'Sombrero'], ['hymenophore', 'Himenóforo'], ['stipe', 'Estípite'], ['habitat', 'Hábitat']];
export async function photoDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(new Error('No pudimos leer la fotografía.')); reader.readAsDataURL(file); });
}
export default function PhotoPicker({ value, onChange, photographer = '', onBusyChange }: { value: PendingPhoto[]; onChange: (v: PendingPhoto[]) => void; photographer?: string; onBusyChange?: (busy: boolean) => void }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { onBusyChange?.(busy); }, [busy, onBusyChange]);
  const urls = useRef(new Set<string>()); const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; urls.current.forEach(url => URL.revokeObjectURL(url)); }; }, []);
  const max = config.demo ? 2 : 10;
  async function add(files: File[]) {
    setError(''); setBusy(true); const created: PendingPhoto[] = [];
    try {
      if (files.length + value.length > 10) throw new Error('Selecciona como máximo 10 fotografías por carga.');
      for (const file of files) {
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error(`${file.name}: usa JPG, PNG o WebP.`);
        if (file.size > max * 1024 * 1024) throw new Error(`${file.name}: el máximo es ${max} MB por imagen.`);
        const preview = URL.createObjectURL(file); urls.current.add(preview);
        // Check that the file decodes, rather than trusting only its extension/MIME.
        try { await new Promise<void>((resolve, reject) => { const img = new Image(); img.onload = () => resolve(); img.onerror = () => reject(new Error(`${file.name}: el archivo no contiene una imagen válida.`)); img.src = preview; }); }
        catch (e) { URL.revokeObjectURL(preview); urls.current.delete(preview); throw e; }
        created.push({ id: crypto.randomUUID(), file, preview, metadata: { url: '', fileName: file.name, photoType: 'habitus', photographer, rightsHolder: photographer, license: '', mimeFormat: file.type } });
      }
      if (active.current) onChange([...value, ...created]);
    } catch (e) { created.forEach(p => { URL.revokeObjectURL(p.preview); urls.current.delete(p.preview); }); if (active.current) setError((e as Error).message); }
    finally { if (active.current) setBusy(false); }
  }
  return <section><label className="upload-drop"><strong>{busy ? 'Revisando imágenes…' : 'Añadir fotografías del macromiceto'}</strong><span>JPG, PNG o WebP · hasta {max} MB por foto · máximo 10 por carga</span><input type="file" multiple disabled={busy} accept="image/jpeg,image/png,image/webp" aria-label="Seleccionar fotografías" onChange={e => { const files = Array.from(e.target.files || []); e.target.value = ''; void add(files); }} /></label>{error && <Notice error>{error}</Notice>}
    {value.map((p, i) => <fieldset className="entry-card photo-entry" key={p.id}><legend>Fotografía {i + 1}</legend><img className="photo-preview" src={p.preview} alt={`Vista previa de ${p.file.name}`} /><Fields value={p.metadata} fields={[
      { key: 'photoType', label: 'Tipo de fotografía', options: photoTypes }, { key: 'photographer', label: 'Fotógrafo/a' }, { key: 'rightsHolder', label: 'Titular de derechos' },
      { key: 'license', label: 'Licencia o permiso de uso', options: [['', 'Sin licencia declarada'], ['https://creativecommons.org/licenses/by/4.0/', 'CC BY 4.0'], ['https://creativecommons.org/licenses/by/3.0/', 'CC BY 3.0'], ['https://creativecommons.org/licenses/by-nc/4.0/', 'CC BY-NC 4.0'], ['https://creativecommons.org/publicdomain/zero/1.0/', 'CC0'], ['All rights reserved', 'Todos los derechos reservados']] },
    ]} onChange={(key, v) => onChange(value.map(item => item.id === p.id ? { ...item, metadata: { ...item.metadata, [key]: v } } : item))} /><details className="photo-credit-editor"><summary>Personas acreditadas y afiliación</summary><ParticipantsEditor media value={p.metadata.credits || []} onChange={credits => onChange(value.map(item => item.id === p.id ? { ...item, metadata: { ...item.metadata, credits } } : item))} /></details><button type="button" className="text-button danger" onClick={() => { URL.revokeObjectURL(p.preview); urls.current.delete(p.preview); onChange(value.filter(item => item.id !== p.id)); }}>Quitar fotografía {i + 1}</button></fieldset>)}
  </section>;
}
