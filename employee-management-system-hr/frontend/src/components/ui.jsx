import { createContext, useCallback, useContext, useState } from 'react'
import { Check, Users, X } from 'lucide-react'

const ToastContext = createContext(() => {})
export const useToast = () => useContext(ToastContext)

export function ToastProvider({ children }) {
  const [notice, setNotice] = useState(null)
  const flash = useCallback((text, type = 'success') => {
    setNotice({ text, type })
    setTimeout(() => setNotice(null), 4000)
  }, [])
  return (
    <ToastContext.Provider value={flash}>
      {children}
      {notice && (
        <div className={'toast ' + notice.type} role="status">
          <span>{notice.type === 'error' ? <X size={17} /> : <Check size={17} />}</span>
          {notice.text}
          <button onClick={() => setNotice(null)} aria-label="Dismiss"><X size={15} /></button>
        </div>
      )}
    </ToastContext.Provider>
  )
}

export function Modal({ title, close, children }) {
  return (
    <div className="backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) close() }}>
      <section className="modal" role="dialog" aria-label={title}>
        <div className="modal-title">
          <div><div className="kicker">PEOPLEDESK HR</div><h2>{title}</h2></div>
          <button className="icon-btn" type="button" onClick={close} aria-label="Close"><X /></button>
        </div>
        {children}
      </section>
    </div>
  )
}

export function ConfirmDialog({ title = 'Are you sure?', text, confirmLabel = 'Confirm', onConfirm, onCancel }) {
  return (
    <div className="backdrop">
      <div className="confirm" role="alertdialog">
        <h2>{title}</h2><p>{text}</p>
        <div className="modal-actions">
          <button className="btn secondary" onClick={onCancel}>Cancel</button>
          <button className="btn danger" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}

export const Status = ({ status }) => (
  <span className={'status ' + String(status).toLowerCase().replace(/\s/g, '-')}><i />{status || '—'}</span>
)

export const Empty = ({ text }) => <div className="empty"><Users size={23} /><span>{text}</span></div>

export const Loading = ({ text = 'Loading…' }) => <div className="empty" aria-busy="true"><span>{text}</span></div>

export const money = (v) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(v || 0))

export function PageHeading({ kicker, title, subtitle, children }) {
  return (
    <div className="heading">
      <div><div className="kicker">{kicker}</div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
      {children && <div className="actions">{children}</div>}
    </div>
  )
}
