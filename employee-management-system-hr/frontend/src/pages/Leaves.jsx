import { useState } from 'react'
import { Check, Plus, X } from 'lucide-react'
import api, { errorMessage } from '../api/client'
import useLoad from '../api/useLoad'
import { useAuth } from '../auth/AuthContext'
import { Empty, Loading, Modal, PageHeading, Status, useToast } from '../components/ui'

const TYPES = ['Annual', 'Sick', 'Casual', 'Unpaid', 'Other']
const today = () => new Date().toISOString().slice(0, 10)

export default function Leaves() {
  const { isAdmin } = useAuth()
  const flash = useToast()
  const [status, setStatus] = useState('')
  const { data, loading, error, reload } = useLoad('/api/leaves', { status: status || undefined })
  const [form, setForm] = useState(false)
  const [review, setReview] = useState(null) // { leave, decision }
  const items = data?.items || []

  const cancel = async (l) => {
    try { await api.post(`/api/leaves/${l.id}/cancel`); flash('Leave request cancelled'); reload() } catch (e) { flash(errorMessage(e), 'error') }
  }

  return (
    <>
      <PageHeading kicker="TIME OFF" title="Leave requests" subtitle={isAdmin ? 'Review and approve or reject leave requests.' : 'Request time off and track the status.'}>
        {!isAdmin && <button className="btn primary" onClick={() => setForm(true)}><Plus size={16} /> Request leave</button>}
      </PageHeading>
      <section className="panel">
        <div className="toolbar"><div className="filters">
          <select aria-label="Status filter" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>{['Pending', 'Approved', 'Rejected', 'Cancelled'].map((s) => <option key={s}>{s}</option>)}</select></div></div>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="table-wrap"><table>
          <thead><tr>{isAdmin && <th>EMPLOYEE</th>}<th>TYPE</th><th>FROM</th><th>TO</th><th>DAYS</th><th>REASON</th><th>STATUS</th><th>REVIEW NOTE</th><th>ACTIONS</th></tr></thead>
          <tbody>
            {loading && !data ? <tr><td colSpan={9}><Loading /></td></tr> : items.map((l) => (
              <tr key={l.id}>
                {isAdmin && <td><b>{l.employee_name}</b><small className="sub">{l.employee_code}</small></td>}
                <td>{l.leave_type}</td><td>{l.start_date}</td><td>{l.end_date}</td><td>{l.days}</td><td className="wrap">{l.reason}</td>
                <td><Status status={l.status} /></td><td className="wrap">{l.review_note || '—'}</td>
                <td>{l.status === 'Pending' && (isAdmin ? <>
                  <button className="btn secondary small" onClick={() => setReview({ leave: l, decision: 'Approved' })}><Check size={14} /> Approve</button>{' '}
                  <button className="btn secondary small danger-text" onClick={() => setReview({ leave: l, decision: 'Rejected' })}><X size={14} /> Reject</button></>
                  : <button className="btn secondary small" onClick={() => cancel(l)}>Cancel</button>)}</td>
              </tr>))}
            {!loading && !items.length && <tr><td colSpan={9}><Empty text="No leave requests." /></td></tr>}
          </tbody></table></div>
      </section>
      {form && !isAdmin && <LeaveForm onClose={() => setForm(false)} onSaved={() => { setForm(false); reload() }} />}
      {review && isAdmin && <ReviewForm {...review} onClose={() => setReview(null)} onSaved={() => { setReview(null); reload() }} />}
    </>
  )
}

function LeaveForm({ onClose, onSaved }) {
  const flash = useToast()
  const [form, setForm] = useState({ leave_type: 'Casual', start_date: today(), end_date: today(), reason: '' })
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    try { await api.post('/api/leaves', form); flash('Leave request submitted'); onSaved() } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }
  return (
    <Modal title="Request leave" close={onClose}>
      <form onSubmit={submit}>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="form-grid">
          <label>Leave type<select value={form.leave_type} onChange={set('leave_type')}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select></label>
          <span />
          <label>From *<input required type="date" value={form.start_date} onChange={set('start_date')} /></label>
          <label>To *<input required type="date" min={form.start_date} value={form.end_date} onChange={set('end_date')} /></label>
          <label className="wide-field">Reason *<textarea required maxLength={1000} value={form.reason} onChange={set('reason')} /></label>
        </div>
        <div className="modal-actions"><button type="button" className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? 'Submitting…' : 'Submit request'}</button></div>
      </form>
    </Modal>
  )
}

function ReviewForm({ leave, decision, onClose, onSaved }) {
  const flash = useToast()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    try { await api.put(`/api/leaves/${leave.id}/review`, { status: decision, review_note: note }); flash(`Leave ${decision.toLowerCase()}`); onSaved() }
    catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }
  return (
    <Modal title={`${decision === 'Approved' ? 'Approve' : 'Reject'} leave`} close={onClose}>
      <form onSubmit={submit}>
        {error && <div className="form-error" role="alert">{error}</div>}
        <p><b>{leave.employee_name}</b> — {leave.leave_type}, {leave.start_date} to {leave.end_date} ({leave.days} day{leave.days > 1 ? 's' : ''})</p>
        <p className="muted">“{leave.reason}”</p>
        <label className="wide-field">Note to employee (optional)<textarea maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} /></label>
        <div className="modal-actions"><button type="button" className="btn secondary" onClick={onClose}>Cancel</button>
          <button className={`btn ${decision === 'Approved' ? 'primary' : 'danger'}`} disabled={busy}>{busy ? 'Saving…' : decision === 'Approved' ? 'Approve' : 'Reject'}</button></div>
      </form>
    </Modal>
  )
}
