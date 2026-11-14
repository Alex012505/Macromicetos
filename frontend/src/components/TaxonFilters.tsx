import type { Taxon } from '../types';
import { TAXON_LEVELS, cascadeOptions, hasTaxonFilters } from '../lib/taxon-filters.mjs';

export default function TaxonFilters({ taxa, value, onChange, onReset, showTitle = false }: {
  taxa: Taxon[];
  value: Record<string, string>;
  onChange: (key: string, value: string) => void;
  onReset?: () => void;
  showTitle?: boolean;
}) {
  const options = cascadeOptions(taxa, value) as Record<string, string[]>;
  return <div className="taxon-filters">
    {showTitle && <p className="taxon-filters-title">Taxonomía</p>}
    {TAXON_LEVELS.map(([key, label]) => <label key={key}>
      <span>{label}</span>
      <select aria-label={`Filtrar por ${label.toLowerCase()}`} value={value[key] || ''} onChange={e => onChange(key, e.target.value)}>
        <option value="">Todos</option>
        {options[key].map(option => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>)}
    {onReset && hasTaxonFilters(value) && <button type="button" className="text-button" onClick={onReset}>Limpiar filtros taxonómicos</button>}
  </div>;
}
