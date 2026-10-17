import { useState } from 'react';
import { Download } from 'lucide-react';
import type { Occurrence, Taxon } from '../types';
import { exportData } from '../lib/downloads';
import { Notice } from './UI';
export default function ExportButtons({ taxa, records, scope }: { taxa: Taxon[]; records: Occurrence[]; scope: 'species' | 'records' }) {
  const [busy, setBusy] = useState(''); const [error, setError] = useState('');
  async function run(format: 'csv' | 'xlsx') { setBusy(format); setError(''); try { await exportData(format, scope, taxa, records); } catch { setError('No se pudo generar el archivo. Intenta nuevamente.'); } finally { setBusy(''); } }
  return <div className="export-controls"><div className="heading-actions">{(['csv', 'xlsx'] as const).map(format => <button className="btn small" key={format} disabled={!!busy || !(scope === 'species' ? taxa.length : records.length)} onClick={() => void run(format)}><Download size={16} />{busy === format ? 'Generando…' : format === 'csv' ? 'Exportar CSV' : 'Exportar Excel'}</button>)}</div>{error && <Notice error>{error}</Notice>}</div>;
}
