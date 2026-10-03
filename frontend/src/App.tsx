import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  BookOpen, Check, ChevronDown, ChevronLeft, ChevronRight, ClipboardList,
  Download, ExternalLink, Flower2, Globe2, Image, LayoutDashboard, Leaf,
  LogIn, LogOut, MapPin, Menu, Microscope, Plus, Search,
  ShieldCheck, SlidersHorizontal, Sprout, Users, X,
} from 'lucide-react';
import { api, config, http } from './lib/api';
import { loadDemo, saveDemo, demoUserForRole } from './data/demo';
import { canAccessPage, canEditOccurrence, capabilitiesFor } from './lib/permissions.mjs';
import { roleNames, statusNames, type Dataset, type Occurrence, type Role, type Status, type Taxon, type User } from './types';
import { Busy, Empty, Modal, Notice, Photo, StatusBadge } from './components/UI';
import OccurrenceMap from './components/OccurrenceMap';
import { AuthForm, RecordForm, TaxonForm, UploadForm } from './components/Forms';
import SpeciesDetail from './components/SpeciesDetail';
import UserManagement from './components/UserManagement';

type Page = 'dashboard' | 'especies' | 'mapa' | 'galeria' | 'registros' | 'curaduria' | 'usuarios' | 'guia';
const pageTitles: Record<Page, string> = { dashboard: 'Vista general', especies: 'Catálogo de especies', mapa: 'Visor cartográfico', galeria: 'Galería multimedia', registros: 'Registros de campo', curaduria: 'Curaduría', usuarios: 'Gestión de usuarios', guia: 'Guía de la plataforma' };
const blank: Dataset = { taxa: [], occurrences: [], users: [] };
const demoSession: User = demoUserForRole('admin');
function currentRoute() {
  const hash = window.location.hash.replace(/^#\/?/, '').split('/');
  return { page: (hash[0] in pageTitles ? hash[0] : hash[0] === 'especie' ? 'especies' : 'dashboard') as Page,
    speciesId: hash[0] === 'especie' ? decodeURIComponent(hash[1] || '') : '' };
}
function dateLabel(value: string) {
  if (!value) return 'Sin fecha';
  const date = new Date(value.includes('T') ? value : value + 'T12:00:00');
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'America/Bogota' }).format(date);
}
export default function App() {
  const [route, setRoute] = useState(currentRoute);
  const [data, setData] = useState<Dataset>(() => config.demo ? loadDemo() : blank);
  const [user, setUser] = useState<User | null>(config.demo ? demoSession : null);
  const [loading, setLoading] = useState(!config.demo);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [query, setQuery] = useState('');
  const [mobileNav, setMobileNav] = useState(false);
  const [modal, setModal] = useState<'auth' | 'record' | 'taxon' | 'upload' | null>(null);
  const [editRecord, setEditRecord] = useState<Occurrence | undefined>();
  const role = user?.role || 'readonly_user';
  const { write: canWrite, curate: canCurate } = capabilitiesFor(role);
  const canEdit = (o: Occurrence) => canEditOccurrence(role, user?.id || '', o);
  const ownRecords = data.occurrences.filter(o => o.ownerId === user?.id);
  const scopeText = {
    readonly_user: 'Consulta fichas, fotografías y observaciones para tu estudio.',
    researcher: 'Documenta hallazgos de campo y gestiona tus propios registros.',
    curator: 'Revisa la identificación y calidad de las observaciones recibidas.',
    admin: 'Coordina registros, curaduría y permisos de la plataforma académica.',
  }[role];
  const pending = data.occurrences.filter(o => o.status === 'pending').length;
  function navigate(page: Page, speciesId?: string) {
    window.location.hash = speciesId ? `/especie/${encodeURIComponent(speciesId)}` : `/${page}`;
    setMobileNav(false); setQuery(''); window.scrollTo({ top: 0, behavior: 'instant' });
  }
  function openSpecies(taxonId: string) { navigate('especies', taxonId); }
  function notify(message: string) { setToast(message); }
  function updateDataset(next: Dataset) { if (config.demo) saveDemo(next); setData(next); }
  async function reload() {
    if (config.demo) { setData(loadDemo()); return; }
    setLoading(true); setError('');
    // Catalog is mandatory. Optional resources fail visibly, without demo fallback.
    const results = await Promise.allSettled([api.taxa(), api.occurrences(), role === 'admin' ? api.users() : Promise.resolve([])]);
    const failures = results.filter((r): r is PromiseRejectedResult => r.status === 'rejected');
    setData({ taxa: results[0].status === 'fulfilled' ? results[0].value : [],
      occurrences: results[1].status === 'fulfilled' ? results[1].value : [],
      users: results[2].status === 'fulfilled' ? results[2].value : [] });
    if (failures.length) setError(failures.map(r => r.reason.message).join(' · '));
    setLoading(false);
  }
  useEffect(() => {
    const listener = () => { if (window.location.hash !== '#main-content') setRoute(currentRoute()); };
    const expired = () => { setUser(null); setModal('auth'); setData(blank); notify('Tu sesión terminó. Inicia sesión nuevamente.'); };
    window.addEventListener('hashchange', listener);
    window.addEventListener('macromicetos-session-expired', expired);
    return () => { window.removeEventListener('hashchange', listener); window.removeEventListener('macromicetos-session-expired', expired); };
  }, []);
  useEffect(() => { if (!config.demo) void reload(); }, [user?.id, role]);
  useEffect(() => { document.title = `${route.speciesId ? 'Ficha de especie' : pageTitles[route.page]} · Macromicetos`; }, [route]);
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''), 5500); return () => clearTimeout(timer); }, [toast]);
  const visibleTaxa = useMemo(() => data.taxa.filter(t => `${t.scientificName} ${t.commonName} ${t.family}`.toLowerCase().includes(query.toLowerCase())), [data.taxa, query]);
  const selected = data.taxa.find(t => t.id === route.speciesId);
  function newRecord() { setEditRecord(undefined); setModal(canWrite ? 'record' : 'auth'); }
  function editOccurrence(o: Occurrence) {
    if (!canEdit(o)) { notify('Solo puedes editar tus propios registros.'); return; }
    setEditRecord(o); setModal('record');
  }
  async function saveOccurrence(record: Occurrence) {
    if (!canWrite) throw new Error('Tu rol no permite guardar registros.');
    const previous = data.occurrences.find(o => o.id === record.id);
    if (previous && !canEdit(previous)) throw new Error('No tienes permiso para editar este registro.');
    if (config.demo) {
      const exists = data.occurrences.some(o => o.id === record.id);
      updateDataset({ ...data, occurrences: exists ? data.occurrences.map(o => o.id === record.id ? record : o) : [record, ...data.occurrences] });
    } else { await api.saveOccurrence(record); await reload(); }
    setModal(null); notify(config.demo ? 'Registro guardado en la demostración local.' : 'Registro enviado al servidor.');
  }
  async function saveTaxon(taxon: Taxon) {
    if (!canWrite) throw new Error('Tu rol no permite crear especies.');
    if (config.demo) updateDataset({ ...data, taxa: [...data.taxa, taxon] });
    else { await api.createTaxon(taxon); await reload(); }
    setModal(null); notify(config.demo ? 'Especie añadida al catálogo de demostración.' : 'Especie enviada al servidor.');
  }
  async function review(o: Occurrence, next: Status, note: string) {
    if (!canCurate) throw new Error('Tu rol no permite revisar registros.');
    if (config.demo) updateDataset({ ...data, occurrences: data.occurrences.map(r => r.id === o.id ? { ...r, status: next, reviewNote: note } : r) });
    else { await api.curate(o, next, note); await reload(); }
    notify(next === 'verified' ? 'Registro verificado.' : 'Registro devuelto con observaciones.');
  }
  function exportCsv(records: Occurrence[]) {
    const cell = (v: string) => `"${v.replace(/^[=+@-]/, "'$&").replaceAll('"', '""')}"`;
    const rows = [['id', 'especie', 'departamento', 'localidad', 'fecha', 'estado'], ...records.map(o => [o.id, data.taxa.find(t => t.id === o.taxonId)?.scientificName || '', o.department, o.locality, o.date, statusNames[o.status]])];
    const blob = new Blob(['\uFEFF' + rows.map(r => r.map(cell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = config.demo ? 'macromicetos-registros-DEMO.csv' : 'macromicetos-registros.csv'; a.click(); URL.revokeObjectURL(url);
  }
  const restricted = !canAccessPage(role, route.page);
  const navItems = [
    { page: 'dashboard' as Page, label: 'Vista general', icon: LayoutDashboard },
    { page: 'especies' as Page, label: 'Catálogo de especies', icon: Flower2 },
    { page: 'mapa' as Page, label: 'Visor cartográfico', icon: MapPin },
    { page: 'galeria' as Page, label: 'Galería multimedia', icon: Image },
  ];
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Saltar al contenido</a>
    {mobileNav && <button className="nav-backdrop" aria-label="Cerrar navegación" onClick={() => setMobileNav(false)} />}
    <aside className={`sidebar ${mobileNav ? 'open' : ''}`} aria-label="Navegación principal">
      <button className="brand academic-brand" onClick={() => navigate('dashboard')} aria-label="Macromicetos, ir al inicio"><span className="brand-mark"><Sprout size={28} /></span><span>Macromicetos<span className="brand-caption">REGISTRO ACADÉMICO</span></span></button>
      <div className="project-label"><span className="project-symbol"><Leaf size={15} /></span><span>Orinoquía colombiana</span></div>
      <nav><p className="nav-label">EXPLORAR</p>{navItems.map(({ page, label, icon: Icon }) => <button key={page} className={`nav-item ${route.page === page ? 'active' : ''}`} onClick={() => navigate(page)} aria-current={route.page === page ? 'page' : undefined}><Icon size={19} /><span>{label}</span>{route.page === page && <span className="nav-active-dot" />}</button>)}
        {(canWrite || canCurate) && <p className="nav-label research-label">INVESTIGACIÓN</p>}
        {canWrite && <button className={`nav-item ${route.page === 'registros' ? 'active' : ''}`} onClick={() => navigate('registros')}><ClipboardList size={19} /><span>Registros de campo</span></button>}
        {canCurate && <button className={`nav-item ${route.page === 'curaduria' ? 'active' : ''}`} onClick={() => navigate('curaduria')}><ShieldCheck size={19} /><span>Curaduría</span>{pending > 0 && <span className="nav-count">{pending}</span>}</button>}
        {role === 'admin' && <button className={`nav-item ${route.page === 'usuarios' ? 'active' : ''}`} onClick={() => navigate('usuarios')}><Users size={19} /><span>Gestión de usuarios</span></button>}
      </nav>
      <div className="sidebar-bottom"><div className="field-note"><span className="eyebrow">INVESTIGACIÓN Y BIODIVERSIDAD</span><p>Registros estandarizados<br />para el conocimiento científico.</p><Leaf size={23} /></div>
        <button className={`nav-item ${route.page === 'guia' ? 'active' : ''}`} onClick={() => navigate('guia')}><BookOpen size={18} />Guía de la plataforma</button>
        <div className="sidebar-footer"><span>PLATAFORMA ACADÉMICA</span><span>v1.0</span></div>
      </div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="topbar-location"><button className="icon-btn mobile-menu" aria-label="Abrir navegación" onClick={() => setMobileNav(true)}><Menu size={22} /></button><span className="breadcrumb">Plataforma académica</span><span className="breadcrumb-divider">/</span><strong>{route.speciesId ? 'Ficha de especie' : pageTitles[route.page]}</strong></div>
        <div className="topbar-actions"><span className={`mode-badge ${config.demo ? 'demo' : ''}`}>{config.demo ? 'Demostración' : 'Modo API'}</span>
          {user ? <div className="user-control"><span className="avatar">{user.name.split(' ').map(n => n[0]).slice(0, 2).join('')}</span><div className="user-label"><strong>{user.name}</strong>{config.demo ? <select aria-label="Rol de demostración" value={role} onChange={e => { setUser(demoUserForRole(e.target.value as Role)); navigate('dashboard'); }}>{Object.entries(roleNames).map(([key, label]) => <option key={key} value={key}>{label} · demo</option>)}</select> : <span>{roleNames[role]}</span>}</div><button className="icon-btn" title="Cerrar sesión" aria-label="Cerrar sesión" onClick={() => { http.setTokens(); setUser(null); if (!config.demo) setData(blank); navigate('dashboard'); }}><LogOut size={17} /></button></div>
          : <button className="btn small" onClick={() => setModal('auth')}><LogIn size={16} />Iniciar sesión</button>}
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        {error && <Notice error><strong>No pudimos cargar toda la información.</strong> {error} <button className="text-button" onClick={() => void reload()}>Reintentar</button></Notice>}
        {loading ? <Busy /> : restricted ? <Empty title="Este espacio requiere otro rol">Tu sesión actual permite explorar el catálogo. Inicia sesión con un rol autorizado para acceder.</Empty> : route.speciesId ? <SpeciesDetail taxon={selected} taxonId={route.speciesId} records={data.occurrences} onBack={() => navigate('especies')} onEdit={canWrite ? editOccurrence : undefined} canEditRecord={canEdit} /> : <>
          {route.page === 'dashboard' && <>
            <div className="page-heading"><div><span className="eyebrow">REGISTRO ACADÉMICO · {roleNames[role].toUpperCase()}</span><h1>Registro de macromicetos<span className="heading-dot">.</span></h1><p>{scopeText}</p></div>{canWrite ? <button className="btn primary" onClick={newRecord}><Plus size={18} />Nuevo registro</button> : canCurate ? <button className="btn primary" onClick={() => navigate('curaduria')}><ShieldCheck size={18} />Revisar observaciones</button> : <button className="btn primary" onClick={() => navigate('especies')}><Search size={18} />Consultar catálogo</button>}</div>
            <section className="hero-banner"><div className="hero-photo" /><div className="hero-copy"><span className="hero-kicker"><span /> BIODIVERSIDAD · ORINOQUÍA COLOMBIANA</span><h2>Observaciones de campo.<br />Conocimiento científico.</h2><p>Consulta el catálogo taxonómico y la distribución de los registros.<br />Un espacio académico para documentar la diversidad de macromicetos.</p><button className="btn hero-btn" onClick={() => navigate('especies')}>Consultar especies <Flower2 size={17} /></button></div><span className="hero-caption">Pleurotus ostreatus · fotografía de referencia</span></section>
            <div className="stats-grid"><Metric label="Especies en el catálogo" value={data.taxa.length} detail="Diversidad documentada" icon={Flower2} color="green" /><Metric label={role === 'researcher' ? 'Mis registros de campo' : 'Registros de campo'} value={role === 'researcher' ? ownRecords.length : data.occurrences.length} detail={role === 'researcher' ? 'Observaciones de mi autoría' : 'Observaciones disponibles'} icon={ClipboardList} color="blue" />{canCurate ? <Metric label="Pendientes de curaduría" value={pending} detail="Registros por revisar" icon={ShieldCheck} color="amber" /> : role === 'researcher' ? <Metric label="Mis registros en revisión" value={ownRecords.filter(o => o.status === 'pending').length} detail="Pendientes de decisión" icon={ShieldCheck} color="amber" /> : <Metric label="Fotografías disponibles" value={data.occurrences.reduce((n, o) => n + o.images.length, 0)} detail="Multimedia asociada" icon={Image} color="amber" />}<Metric label="Departamentos" value={new Set(data.occurrences.map(o => o.department).filter(Boolean)).size} detail="Cobertura del territorio" icon={MapPin} color="purple" /></div>
            <div className="dashboard-grid"><section className="panel recent-panel"><div className="section-head"><div><h2>Últimas observaciones</h2><p>Observaciones de campo más recientes.</p></div><button className="text-button" onClick={() => navigate(canWrite ? 'registros' : 'especies')}>Ver todos <ChevronRight size={15} /></button></div>
              <RecordTable records={data.occurrences.slice(0, 5)} taxa={data.taxa} onSelect={o => openSpecies(o.taxonId)} />
              <div className="panel-foot"><Leaf size={14} /><span>{config.demo ? 'Datos ilustrativos para revisar la experiencia de navegación.' : 'Información obtenida de la API del proyecto.'}</span></div>
            </section><div className="dashboard-aside"><section className="panel territory-panel"><div className="section-head"><div><h2>El territorio, en el mapa</h2><p>Un vistazo a las observaciones.</p></div><Globe2 size={21} /></div><OccurrenceMap compact records={data.occurrences} taxa={data.taxa} onSelect={o => openSpecies(o.taxonId)} /><div className="territory-footer"><span><i />{data.occurrences.filter(o => o.lat != null && o.lng != null).length} puntos georreferenciados</span><button className="text-button" onClick={() => navigate('mapa')}>Abrir visor <ChevronRight size={15} /></button></div></section>
              <section className="contribute-panel"><span className="contribute-icon"><Microscope size={23} /></span><div><h3>{canWrite ? 'Documentación de campo' : canCurate ? 'Revisión científica' : 'Consulta para el estudio'}</h3><p>{scopeText}</p>{canWrite ? <button className="text-button" onClick={newRecord}>Registrar un hallazgo <Plus size={15} /></button> : <button className="text-button" onClick={() => navigate(canCurate ? 'curaduria' : 'mapa')}>{canCurate ? 'Abrir cola de revisión' : 'Explorar observaciones en el mapa'}<ChevronRight size={15} /></button>}</div></section></div></div>
            <div className="section-head highlights-head"><div><span className="eyebrow">DEL CATÁLOGO</span><h2>Especies del catálogo</h2></div><button className="text-button" onClick={() => navigate('especies')}>Ver catálogo <ChevronRight size={15} /></button></div><div className="highlight-grid">{data.taxa.slice(0, 4).map(t => <SpeciesCard key={t.id} taxon={t} count={data.occurrences.filter(o => o.taxonId === t.id).length} onClick={() => openSpecies(t.id)} />)}</div>
          </>}
          {route.page === 'especies' && <Catalog taxa={visibleTaxa} records={data.occurrences} query={query} setQuery={setQuery} onSelect={openSpecies} onCreate={canWrite ? () => setModal('taxon') : undefined} />}
          {route.page === 'mapa' && <MapView data={data} onSelect={o => openSpecies(o.taxonId)} />}
          {route.page === 'galeria' && <Gallery data={data} onSelect={openSpecies} onUpload={canWrite ? () => setModal('upload') : undefined} />}
          {route.page === 'registros' && <RecordsView ownOnly={role === 'researcher'} data={{ ...data, occurrences: role === 'researcher' ? ownRecords : data.occurrences }} onSelect={editOccurrence} onCreate={newRecord} onExport={exportCsv} onFetched={o => { if (!data.occurrences.some(r => r.id === o.id)) setData({ ...data, occurrences: [o, ...data.occurrences] }); }} />}
          {route.page === 'curaduria' && <Curation data={data} onReview={review} onSpecies={openSpecies} />}
          {route.page === 'usuarios' && <UserManagement users={data.users} onSave={async (updated) => {
            if (role !== 'admin') throw new Error('Solo el administrador puede gestionar roles.');
            if (config.demo) updateDataset({ ...data, users: data.users.map(u => u.id === updated.id ? updated : u) });
            else { await api.updateUserRole(updated.id, updated.role); await reload(); }
            if (user?.id === updated.id) setUser(updated);
            notify(config.demo ? 'Rol actualizado en la demostración.' : 'Rol enviado al servidor.');
          }} />}
          {route.page === 'guia' && <Guide />}
        </>}
        <footer className="app-footer"><span><Sprout size={15} />Registro académico de macromicetos · Orinoquía colombiana</span><button className="text-button" onClick={() => navigate('guia')}>Sobre los datos y las fotografías</button></footer>
      </main>
    </div>
    {toast && <div className="toast" role="status"><Check size={18} /><span>{toast}</span><button className="icon-btn" aria-label="Cerrar notificación" onClick={() => setToast('')}><X size={16} /></button></div>}
    {modal === 'auth' && <Modal title="Acceso a la plataforma académica" onClose={() => setModal(null)}><AuthForm onSuccess={u => { setUser(u); setModal(null); notify(config.demo ? 'Sesión de demostración iniciada.' : 'Sesión iniciada.'); }} /></Modal>}
    {modal === 'record' && <Modal title={editRecord ? 'Editar registro de campo' : 'Registrar un nuevo hallazgo'} wide onClose={() => setModal(null)}><RecordForm taxa={data.taxa} initial={editRecord} author={user?.name || ''} ownerId={user?.id || ''} onSave={saveOccurrence} onCancel={() => setModal(null)} /></Modal>}
    {modal === 'taxon' && <Modal title="Añadir una especie al catálogo" wide onClose={() => setModal(null)}><TaxonForm existing={data.taxa} onSave={saveTaxon} onCancel={() => setModal(null)} /></Modal>}
    {modal === 'upload' && <Modal title="Añadir fotografía" onClose={() => setModal(null)}><UploadForm records={data.occurrences.filter(canEdit)} taxa={data.taxa} onDone={async (recordId, url) => { if (config.demo && url) updateDataset({ ...data, occurrences: data.occurrences.map(o => o.id === recordId ? { ...o, images: [...o.images, url] } : o) }); else await reload(); setModal(null); notify(config.demo ? 'Fotografía guardada en la demostración local.' : 'Fotografía enviada al servidor.'); }} /></Modal>}
  </div>;
}

function PageHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: React.ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}<span className="heading-dot">.</span></h1><p>{description}</p></div>{children}</div>;
}
function Metric({ label, value, detail, icon: Icon, color }: { label: string; value: number; detail: string; icon: typeof Flower2; color: string }) {
  return <div className="metric"><div className="metric-top"><span>{label}</span><span className={`metric-icon ${color}`}><Icon size={20} /></span></div><strong className="metric-value">{value.toLocaleString('es-CO')}</strong><span className="metric-detail">{detail}</span></div>;
}
function SpeciesCard({ taxon: t, count, onClick }: { taxon: Taxon; count: number; onClick: () => void }) {
  return <button className="species-card" onClick={onClick}><div className="species-card-photo"><Photo src={t.image} name={t.scientificName} /><span className="photo-tag">{t.family || 'Sin familia'}</span></div><div className="species-card-body"><span className="scientific-name">{t.scientificName}</span><span className="common-name">{t.commonName || 'Sin nombre común'}</span><div className="species-card-foot"><span><MapPin size={13} />{count} {count === 1 ? 'observación' : 'observaciones'}</span><ChevronRight size={17} /></div></div></button>;
}
function RecordTable({ records, taxa, onSelect }: { records: Occurrence[]; taxa: Taxon[]; onSelect: (o: Occurrence) => void }) {
  return records.length ? <div className="table-scroll"><table><thead><tr><th>Especie</th><th>Localización</th><th>Fecha</th><th>Estado</th><th><span className="sr-only">Acción</span></th></tr></thead><tbody>{records.map(o => { const t = taxa.find(t => t.id === o.taxonId); return <tr key={o.id}><td><button className="species-cell" onClick={() => onSelect(o)}><Photo src={o.images[0] || t?.image} name={t?.scientificName || 'Ocurrencia'} /><span><strong className="scientific-name">{t?.scientificName || 'Sin identificación'}</strong><small>{t?.commonName || o.author || 'Registro de campo'}</small></span></button></td><td><span className="location-cell"><MapPin size={13} />{o.department || 'Sin localidad'}</span></td><td className="date-cell">{dateLabel(o.date)}</td><td><StatusBadge status={o.status} /></td><td><button className="icon-btn" aria-label={`Abrir ${t?.scientificName || o.id}`} onClick={() => onSelect(o)}><ChevronRight size={17} /></button></td></tr>; })}</tbody></table></div> : <Empty title="Aún no hay observaciones">Los registros de campo aparecerán aquí cuando estén disponibles.</Empty>;
}
function Catalog({ taxa, records, query, setQuery, onSelect, onCreate }: { taxa: Taxon[]; records: Occurrence[]; query: string; setQuery: (q: string) => void; onSelect: (id: string) => void; onCreate?: () => void }) {
  const [family, setFamily] = useState(''); const [order, setOrder] = useState('name');
  const [layout, setLayout] = useState<'grid' | 'list'>('grid'); const [page, setPage] = useState(1);
  const families = [...new Set(taxa.map(t => t.family).filter(Boolean))].sort();
  const filtered = taxa.filter(t => !family || t.family === family).sort((a, b) => order === 'name' ? a.scientificName.localeCompare(b.scientificName) : records.filter(o => o.taxonId === b.id).length - records.filter(o => o.taxonId === a.id).length);
  const pages = Math.max(1, Math.ceil(filtered.length / 8)); const actualPage = Math.min(page, pages); const items = filtered.slice((actualPage - 1) * 8, actualPage * 8);
  useEffect(() => setPage(1), [query, family, order]);
  return <><PageHeader eyebrow="DIVERSIDAD FÚNGICA" title="Catálogo de macromicetos" description="Encuentra especies, explora su taxonomía y conoce sus observaciones.">{onCreate && <button className="btn primary" onClick={onCreate}><Plus size={17} />Añadir especie</button>}</PageHeader>
    <div className="filter-bar"><label className="search-input"><Search size={18} /><input aria-label="Buscar especies" placeholder="Buscar por nombre, especie o familia…" value={query} onChange={e => setQuery(e.target.value)} />{query && <button className="icon-btn" onClick={() => setQuery('')} aria-label="Limpiar búsqueda"><X size={15} /></button>}</label><select aria-label="Filtrar por familia" value={family} onChange={e => setFamily(e.target.value)}><option value="">Todas las familias</option>{families.map(f => <option key={f}>{f}</option>)}</select><select aria-label="Ordenar especies" value={order} onChange={e => setOrder(e.target.value)}><option value="name">Nombre: A–Z</option><option value="observations">Más observaciones</option></select><div className="view-switch"><button className={layout === 'grid' ? 'selected' : ''} aria-label="Vista de tarjetas" aria-pressed={layout === 'grid'} onClick={() => setLayout('grid')}><LayoutDashboard size={18} /></button><button className={layout === 'list' ? 'selected' : ''} aria-label="Vista de lista" aria-pressed={layout === 'list'} onClick={() => setLayout('list')}><ClipboardList size={18} /></button></div></div>
    <p className="results-label">{filtered.length} {filtered.length === 1 ? 'especie encontrada' : 'especies encontradas'}{query && ` para “${query}”`}</p>
    {!filtered.length ? <Empty title="No encontramos especies">Prueba con otro nombre o cambia los filtros.</Empty> : layout === 'grid' ? <div className="catalog-grid">{items.map(t => <SpeciesCard key={t.id} taxon={t} count={records.filter(o => o.taxonId === t.id).length} onClick={() => onSelect(t.id)} />)}</div> : <section className="panel"><div className="table-scroll"><table><thead><tr><th>Especie</th><th>Familia</th><th>Observaciones</th><th>Estado</th></tr></thead><tbody>{items.map(t => <tr key={t.id}><td><button className="species-cell" onClick={() => onSelect(t.id)}><Photo src={t.image} name={t.scientificName} /><span><strong className="scientific-name">{t.scientificName}</strong><small>{t.commonName}</small></span></button></td><td>{t.family || 'Sin familia'}</td><td>{records.filter(o => o.taxonId === t.id).length}</td><td><StatusBadge status={t.status} /></td></tr>)}</tbody></table></div></section>}
    {filtered.length > 0 && <div className="pagination"><span>Mostrando {(actualPage - 1) * 8 + 1}–{Math.min(actualPage * 8, filtered.length)} de {filtered.length}</span><div><button className="btn small" disabled={actualPage === 1} onClick={() => setPage(actualPage - 1)} aria-label="Página anterior"><ChevronLeft size={16} /></button><span>{actualPage} / {pages}</span><button className="btn small" disabled={actualPage === pages} onClick={() => setPage(actualPage + 1)} aria-label="Página siguiente"><ChevronRight size={16} /></button></div></div>}</>;
}
function MapView({ data, onSelect }: { data: Dataset; onSelect: (o: Occurrence) => void }) {
  const [department, setDepartment] = useState(''); const [family, setFamily] = useState(''); const [verified, setVerified] = useState(false); const [start, setStart] = useState(''); const [end, setEnd] = useState('');
  const filtered = data.occurrences.filter(o => (!department || o.department === department) && (!verified || o.status === 'verified') && (!family || data.taxa.find(t => t.id === o.taxonId)?.family === family) && (!start || o.date >= start) && (!end || o.date.slice(0, 10) <= end));
  const mapped = filtered.filter(o => o.lat != null && o.lng != null);
  return <><PageHeader eyebrow="OBSERVACIONES EN EL TERRITORIO" title="Distribución de observaciones" description="Recorre el mapa y selecciona una observación para abrir su ficha." />
    {!config.demo && !config.occurrencesPath && <Notice>La API actual no define una lista de ocurrencias. Configura esa ruta para visualizar los registros geográficos.</Notice>}
    <div className="map-workspace panel"><aside className="map-filters"><h2><SlidersHorizontal size={18} />Filtros del mapa</h2><label>Departamento<select value={department} onChange={e => setDepartment(e.target.value)}><option value="">Todos los departamentos</option>{[...new Set(data.occurrences.map(o => o.department).filter(Boolean))].map(d => <option key={d}>{d}</option>)}</select></label><label>Familia<select value={family} onChange={e => setFamily(e.target.value)}><option value="">Todas las familias</option>{[...new Set(data.taxa.map(t => t.family).filter(Boolean))].map(f => <option key={f}>{f}</option>)}</select></label><label>Desde<input type="date" value={start} onChange={e => setStart(e.target.value)} /></label><label>Hasta<input type="date" min={start} value={end} onChange={e => setEnd(e.target.value)} /></label><label className="checkbox-label"><input type="checkbox" checked={verified} onChange={e => setVerified(e.target.checked)} />Solo verificados</label><button className="text-button" onClick={() => { setDepartment(''); setFamily(''); setStart(''); setEnd(''); setVerified(false); }}>Restablecer filtros</button><div className="map-legend"><h3>Leyenda</h3><span><i className="legend-dot verified" />Verificado</span><span><i className="legend-dot pending" />En revisión</span><span><i className="legend-dot rejected" />Otros estados</span></div><p className="muted">{mapped.length} puntos en el mapa{filtered.length !== mapped.length && ` · ${filtered.length - mapped.length} registros sin coordenadas`}</p></aside><div className="full-map"><OccurrenceMap records={filtered} taxa={data.taxa} onSelect={onSelect} /><span className="map-count">{config.demo ? 'Coordenadas de demostración' : `${mapped.length} observaciones`}</span></div></div>
    <section className="panel map-results"><div className="section-head"><h2>Observaciones filtradas</h2><span>{filtered.length} resultados</span></div><RecordTable records={filtered} taxa={data.taxa} onSelect={onSelect} /></section></>;
}
function Gallery({ data, onSelect, onUpload }: { data: Dataset; onSelect: (id: string) => void; onUpload?: () => void }) {
  const [query, setQuery] = useState(''); const [lightbox, setLightbox] = useState<{ url: string; name: string; taxonId: string } | null>(null);
  const images = data.occurrences.flatMap(o => o.images.map((url, i) => ({ key: `${o.id}-${i}`, url, record: o, taxon: data.taxa.find(t => t.id === o.taxonId) })));
  const filtered = images.filter(m => `${m.taxon?.scientificName} ${m.taxon?.commonName} ${m.record.department}`.toLowerCase().includes(query.toLowerCase()));
  return <><PageHeader eyebrow="MIRADAS DEL TERRITORIO" title="Archivo fotográfico de macromicetos" description="Fotografías asociadas a las observaciones de campo.">{onUpload && <button className="btn primary" onClick={onUpload}><Plus size={17} />Añadir fotografía</button>}</PageHeader><div className="filter-bar"><label className="search-input"><Search size={18} /><input aria-label="Buscar fotografías" placeholder="Buscar especie o departamento…" value={query} onChange={e => setQuery(e.target.value)} /></label><span className="muted">{filtered.length} fotografías</span></div>{!filtered.length ? <Empty title="Sin fotografías disponibles">Las imágenes vinculadas a los registros aparecerán aquí.</Empty> : <div className="gallery-grid">{filtered.map(m => <button key={m.key} className="gallery-card" onClick={() => setLightbox({ url: m.url, name: m.taxon?.scientificName || 'Sin identificación', taxonId: m.record.taxonId })}><Photo src={m.url} name={m.taxon?.scientificName || 'Hongo'} /><div><strong className="scientific-name">{m.taxon?.scientificName || 'Sin identificación'}</strong><span><MapPin size={13} />{m.record.department} · {dateLabel(m.record.date)}</span></div></button>)}</div>}{config.demo && <p className="image-disclaimer">Fotografías de referencia: no documentan las observaciones ficticias de esta demostración. Consulta los créditos en la guía.</p>}{lightbox && <Modal title={lightbox.name} wide onClose={() => setLightbox(null)}><Photo src={lightbox.url} name={lightbox.name} className="lightbox-photo" /><div className="form-actions"><button className="btn primary" onClick={() => { onSelect(lightbox.taxonId); setLightbox(null); }}>Ver ficha de especie</button></div></Modal>}</>;
}
function RecordsView({ data, ownOnly, onSelect, onCreate, onExport, onFetched }: { data: Dataset; ownOnly: boolean; onSelect: (o: Occurrence) => void; onCreate: () => void; onExport: (o: Occurrence[]) => void; onFetched: (o: Occurrence) => void }) {
  const [query, setQuery] = useState(''); const [status, setStatus] = useState(''); const [id, setId] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const records = data.occurrences.filter(o => (!status || status === o.status) && `${data.taxa.find(t => t.id === o.taxonId)?.scientificName} ${o.department} ${o.author}`.toLowerCase().includes(query.toLowerCase()));
  async function fetchById(e: FormEvent) { e.preventDefault(); setBusy(true); setError(''); try { const o = await api.occurrence(id); onFetched(o); onSelect(o); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  return <><PageHeader eyebrow="CUADERNO DE CAMPO" title={ownOnly ? 'Mis registros de campo' : 'Registros de campo'} description={ownOnly ? 'Crea, edita y consulta las observaciones de tu autoría.' : 'Gestiona las observaciones registradas en la plataforma académica.'}><div className="heading-actions"><button className="btn" disabled={!records.length} onClick={() => onExport(records)}><Download size={17} />Exportar CSV</button><button className="btn primary" onClick={onCreate}><Plus size={17} />Nuevo registro</button></div></PageHeader>
    {!config.demo && !config.occurrencesPath && <><Notice>El contrato actual permite consultar una ocurrencia por ID. El listado general necesita una ruta adicional.</Notice><form className="filter-bar" onSubmit={fetchById}><label className="search-input"><Search size={18} /><input required aria-label="ID de la ocurrencia" placeholder="Consultar una ocurrencia por ID…" value={id} onChange={e => setId(e.target.value)} /></label><button className="btn primary" disabled={busy}>{busy ? 'Consultando…' : 'Consultar'}</button></form>{error && <Notice error>{error}</Notice>}</>}
    <div className="filter-bar"><label className="search-input"><Search size={18} /><input aria-label="Buscar registros" placeholder="Buscar especie, autor o departamento…" value={query} onChange={e => setQuery(e.target.value)} /></label><select aria-label="Filtrar registros por estado" value={status} onChange={e => setStatus(e.target.value)}><option value="">Todos los estados</option>{Object.entries(statusNames).map(([k, label]) => <option key={k} value={k}>{label}</option>)}</select><span className="muted">{records.length} registros</span></div><section className="panel"><RecordTable records={records} taxa={data.taxa} onSelect={onSelect} /></section></>;
}
function Curation({ data, onReview, onSpecies }: { data: Dataset; onReview: (o: Occurrence, s: Status, note: string) => Promise<void>; onSpecies: (id: string) => void }) {
  const [filter, setFilter] = useState<Status>('pending'); const [selectedId, setSelectedId] = useState(''); const [note, setNote] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const records = data.occurrences.filter(o => o.status === filter); const selected = records.find(o => o.id === selectedId) || records[0]; const taxon = data.taxa.find(t => t.id === selected?.taxonId);
  useEffect(() => { setNote(''); setError(''); }, [selected?.id]);
  async function submit(next: Status) { if (!selected) return; if (next === 'rejected' && note.trim().length < 10) { setError('Explica los ajustes necesarios con al menos 10 caracteres.'); return; } setBusy(true); setError(''); try { await onReview(selected, next, note); setNote(''); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  return <><PageHeader eyebrow="CALIDAD Y CONOCIMIENTO" title="Revisión y curaduría" description="Revisa las observaciones y acompaña la calidad de los datos." />{!config.demo && !config.curatePath && <Notice>El backend todavía debe definir la acción de curaduría. La interfaz está preparada; las decisiones solo se guardan localmente en modo demostración.</Notice>}<div className="tabs status-tabs">{(['pending', 'verified', 'rejected'] as Status[]).map(s => <button key={s} className={filter === s ? 'active' : ''} onClick={() => { setFilter(s); setSelectedId(''); }}>{statusNames[s]}<span>{data.occurrences.filter(o => o.status === s).length}</span></button>)}</div><div className="curation-workspace panel"><div className="review-list">{records.length ? records.map(o => { const t = data.taxa.find(t => t.id === o.taxonId); return <button key={o.id} className={`review-list-item ${selected?.id === o.id ? 'selected' : ''}`} onClick={() => setSelectedId(o.id)}><Photo src={o.images[0] || t?.image} name={t?.scientificName || 'Hongo'} /><span><strong className="scientific-name">{t?.scientificName || 'Sin identificación'}</strong><small>{o.department} · {o.author}</small></span><ChevronRight size={16} /></button>; }) : <Empty title="Cola despejada">No hay registros con este estado.</Empty>}</div><div className="review-detail">{selected ? <><div className="section-head"><div><span className="eyebrow">REVISIÓN DEL REGISTRO</span><h2 className="scientific-name">{taxon?.scientificName || 'Sin identificación'}</h2></div><StatusBadge status={selected.status} /></div><Photo src={selected.images[0] || taxon?.image} name={taxon?.scientificName || 'Hongo'} className="review-photo" /><dl className="detail-fields"><div><dt>Identificación propuesta</dt><dd>{taxon?.scientificName || 'Sin identificación'}</dd></div><div><dt>Familia</dt><dd>{taxon?.family || 'Sin dato'}</dd></div><div><dt>Localidad</dt><dd>{selected.locality || 'Sin dato'}</dd></div><div><dt>Registrado por</dt><dd>{selected.author || 'Sin dato'}</dd></div><div><dt>Sustrato</dt><dd>{selected.substrate || 'Sin dato'}</dd></div></dl><button className="text-button" onClick={() => onSpecies(selected.taxonId)}>Consultar ficha completa <ExternalLink size={14} /></button>{selected.reviewNote && <Notice>Observaciones: {selected.reviewNote}</Notice>}{selected.status === 'pending' && <><label className="field review-notes">Observaciones del curador<textarea value={note} onChange={e => setNote(e.target.value)} placeholder="Anota criterios de identificación o ajustes necesarios…" rows={3} maxLength={2000} /></label>{error && <Notice error>{error}</Notice>}<div className="form-actions"><button className="btn" disabled={busy || (!config.demo && !config.curatePath)} onClick={() => void submit('rejected')}>Solicitar ajustes</button><button className="btn primary" disabled={busy || (!config.demo && !config.curatePath)} onClick={() => void submit('verified')}><Check size={17} />{busy ? 'Guardando…' : 'Verificar registro'}</button></div></>}</> : <Empty title="Selecciona un registro para revisar" />}</div></div></>;
}
function Guide() {
  return <><PageHeader eyebrow="PRIMEROS PASOS" title="Guía de uso de la plataforma" description="Una guía breve para moverte por el espacio de investigación." /><div className="guide-grid">{[
    [Flower2, 'Explora el catálogo', 'Busca por nombre científico, nombre común o familia. Abre una ficha para consultar taxonomía, ecología y observaciones.'],
    [MapPin, 'Recorre el territorio', 'Filtra por departamento, familia, fecha y estado. Selecciona un marcador para abrir la ficha de la especie.'],
    [ClipboardList, 'Documenta tus hallazgos', 'Con un rol investigador o administrador puedes registrar observaciones. Cada hallazgo se envía inicialmente a revisión.'],
    [ShieldCheck, 'Acompaña la calidad', 'Curadores y administradores revisan el registro y lo verifican o solicitan ajustes con una observación.'],
  ].map(([Icon, title, text]) => { const Component = Icon as typeof Flower2; return <section className="panel guide-card" key={String(title)}><Component size={28} /><h2>{String(title)}</h2><p>{String(text)}</p></section>; })}</div><section className="panel prose"><h2>Datos de demostración</h2><p>Las métricas se calculan con los registros que estás viendo. En modo demostración, personas, observaciones, coordenadas y medidas son ficticias. Los cambios se guardan únicamente en este navegador. No hay sincronización activa con GBIF ni identificación por inteligencia artificial en esta entrega.</p><h2>Fotografías y créditos</h2><p>Las fotografías son referencias de especies y no pertenecen a las observaciones ficticias del demo. No se usan como evidencia de presencia en la Orinoquía.</p><ul><li><a href="https://commons.wikimedia.org/wiki/File:Pleurotus_ostreatus_JPG7.jpg" target="_blank" rel="noreferrer">Pleurotus ostreatus</a> · Jean-Pol GRANDMONT · <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank" rel="noreferrer">CC BY 3.0</a>. Encuadre visual mediante CSS.</li><li><a href="https://commons.wikimedia.org/wiki/File:Turkey-tail_Trametes_versicolor.JPG_(87dbc148-05ec-4dbb-a830-1194b3d8d3aa).JPG" target="_blank" rel="noreferrer">Trametes versicolor</a> · National Park Service · dominio público en EE. UU.</li></ul><h2>Acceso según tu rol</h2><p>Visitante: catálogo, fichas, mapa y galería. Investigador: crea registros y edita sus propias observaciones; puede añadir fotografías a ellas. Curador: revisión de observaciones. Administrador: todos los módulos, gestión de usuarios y roles. El backend debe comprobar los permisos en cada petición.</p></section></>;
}
