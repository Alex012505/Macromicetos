import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AlertCircle, Check, Flower2, LoaderCircle, X } from 'lucide-react';
import { statusNames, type Status } from '../types';

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge ${status}`}>{status === 'verified' && <Check size={12} />}{statusNames[status]}</span>;
}
export function Photo({ src, name, className = '' }: { src?: string; name: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  return src && !failed ? <img className={`photo ${className}`} src={src} alt={name} loading="lazy" onError={() => setFailed(true)} />
    : <div className={`photo no-photo ${className}`} aria-label={`${name}: sin fotografía`}><Flower2 size={30} /><span>Sin fotografía</span></div>;
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><Flower2 size={34} /><h3>{title}</h3>{children && <p>{children}</p>}</div>;
}
export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <div className={`notice ${error ? 'error' : ''}`} role={error ? 'alert' : 'status'}><AlertCircle size={18} /><div>{children}</div></div>;
}
export function Busy({ children = 'Cargando información…' }: { children?: ReactNode }) {
  return <div className="loading" role="status"><LoaderCircle className="spin" size={22} />{children}</div>;
}
export function Modal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement as HTMLElement | null;
    dialog.showModal();
    const cancel = (event: Event) => { event.preventDefault(); onCloseRef.current(); };
    dialog.addEventListener('cancel', cancel);
    return () => { dialog.removeEventListener('cancel', cancel); dialog.close(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className={`modal ${wide ? 'wide' : ''}`} aria-labelledby="modal-title" onClick={e => { if (e.target === ref.current) onClose(); }}>
    <div className="modal-head"><h2 id="modal-title">{title}</h2><button className="icon-btn" aria-label="Cerrar diálogo" onClick={onClose}><X size={20} /></button></div>
    <div className="modal-body">{children}</div>
  </dialog>;
}
