// Filtros taxonómicos compartidos por el catálogo de especies y el visor del mapa.
// Las claves coinciden con la interfaz Taxon de types.ts.
export const TAXON_LEVELS = [
  ['kingdom', 'Reino'],
  ['phylum', 'Filo'],
  ['className', 'Clase'],
  ['order', 'Orden'],
  ['family', 'Familia'],
  ['genus', 'Género'],
  ['species', 'Especie'],
];

export const EMPTY_TAXON_FILTERS = Object.fromEntries(TAXON_LEVELS.map(([key]) => [key, '']));

// "Especie" usa el nombre científico completo; el resto son columnas del taxón.
const valueOf = (taxon, key) => key === 'species'
  ? String(taxon.scientificName || '')
  : String(taxon[key] || '');

export function hasTaxonFilters(filters = {}) {
  return TAXON_LEVELS.some(([key]) => Boolean(filters[key]));
}

export function matchesTaxonFilters(taxon, filters = {}) {
  // Una ocurrencia sin taxón solo pasa cuando no hay ningún filtro taxonómico.
  if (!taxon) return !hasTaxonFilters(filters);
  return TAXON_LEVELS.every(([key]) => !filters[key] || valueOf(taxon, key) === filters[key]);
}

// Al cambiar un nivel se limpian los niveles inferiores para mantener la cascada coherente.
export function applyTaxonFilter(filters, key, value) {
  const index = TAXON_LEVELS.findIndex(([level]) => level === key);
  const next = { ...filters, [key]: value };
  if (index >= 0) for (const [level] of TAXON_LEVELS.slice(index + 1)) next[level] = '';
  return next;
}

// Opciones de cada nivel limitadas por los niveles superiores ya elegidos.
export function cascadeOptions(taxa, filters = {}) {
  const options = {};
  TAXON_LEVELS.forEach(([key], index) => {
    const parents = TAXON_LEVELS.slice(0, index);
    const values = new Set();
    for (const taxon of taxa) {
      if (!parents.every(([parent]) => !filters[parent] || valueOf(taxon, parent) === filters[parent])) continue;
      const value = valueOf(taxon, key);
      if (value) values.add(value);
    }
    const list = [...values].sort((a, b) => a.localeCompare(b, 'es'));
    // La selección actual nunca desaparece aunque el catálogo cambie.
    if (filters[key] && !list.includes(filters[key])) list.unshift(filters[key]);
    options[key] = list;
  });
  return options;
}
