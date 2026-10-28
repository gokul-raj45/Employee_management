import { useState } from 'react'
import { Edit3, Plus, Trash2 } from 'lucide-react'
import api, { errorMessage } from '../api/client'
import useLoad from '../api/useLoad'
import { useAuth } from '../auth/AuthContext'
import { ConfirmDialog, Empty, Loading, Modal, PageHeading, Status, useToast } from '../components/ui'

const today = () => new Date().toISOString().slice(0, 10)
const STATUSES = ['Present', 'Absent', 'Late', 'Half-day', 'Leave']

export default function Attendance() {
  const { isAdmin } = useAuth()
  const flash = useToast()
  const [range, setRange] = useState({ from: '', to: '' })
  const { data, loading, error, reload } = useLoad('/api/attendance', { from: range.from || undefined, to: range.to || undefined })
  const [modal, setModal] = useState(null)
  const [del, setDel] = useState(null)
  const items = data?.items || []

  const remove = async () => {
    try { await api.delete(`/api/attendance/${del.id}`); flash('Attendance deleted'); setDel(null); reload() }
    catch (e) { flash(errorMessage(e), 'error'); setDel(null) }
  }

  return (
    <>
      <PageHeading kicker="TIME & ATTENDANCE" title="Attendance" subtitle={isAdmin ? 'Create and manage attendance.' : 'Your attendance history.'}>
        {isAdmin && <button className="btn primary" onClick={() => setModal({ record: null })}><Plus size={16} /> Record attendance</button>}
      </PageHeading>
      <section className="panel">
        <div className="toolbar">
          <div className="filters">
            <label className="inline">From <input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>
            <label className="inline">To <input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label>
          </div>
        </div>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="table-wrap"><table>
          <thead><tr><th>EMPLOYEE</th><th>DATE</th><th>STATUS</th><th>CHECK IN</th><th>CHECK OUT</th><th>NOTES</th>{isAdmin && <th>ACTIONS</th>}</tr></thead>
          <tbody>
            {loading && !data ? <tr><td colSpan={7}><Loading /></td></tr> : items.map((a) => (
              <tr key={a.id}>
                <td><b>{a.employee_name}</b><small className="sub">{a.employee_code}</small></td><td>{a.attendance_date}</td><td><Status status={a.status} /></td>
                <td>{a.check_in || '—'}</td><td>{a.check_out || '—'}</td><td>{a.notes || '—'}</td>
                {isAdmin && <td><button className="icon-btn" aria-label="Edit attendance" onClick={() => setModal({ record: a })}><Edit3 size={16} /></button>
                  <button className="icon-btn danger-text" aria-label="Delete attendance" onClick={() => setDel(a)}><Trash2 size={16} /></button></td>}
              </tr>))}
            {!loading && !items.length && <tr><td colSpan={isAdmin ? 7 : 6}><Empty text="No attendance records available." /></td></tr>}
          </tbody></table></div>
      </section>
      {modal && isAdmin && <AttendanceForm record={modal.record} onClose={() => setModal(null)} onSaved={() => { setModal(null); reload() }} />}
      {del && <ConfirmDialog title="Delete this record?" text="This action cannot be undone." confirmLabel="Delete" onConfirm={remove} onCancel={() => setDel(null)} />}
    </>
  )
}

function AttendanceForm({ record, onClose, onSaved }) {
  const flash = useToast()
  const { data: emps } = useLoad('/api/employees', { per_page: 100, status: '' })
  const [form, setForm] = useState(record ? { employee_id: String(record.employee_id), attendance_date: record.attendance_date, status: record.status,
    check_in: record.check_in, check_out: record.check_out, notes: record.notes } : { employee_id: '', attendance_date: today(), status: 'Present', check_in: '09:00', check_out: '18:00', notes: '' })
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    try {
      const body = { ...form, employee_id: Number(form.employee_id) }
      if (record) await api.put(`/api/attendance/${record.id}`, body); else await api.post('/api/attendance', body)
      flash('Attendance saved'); onSaved()
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }
  return (
    <Modal title={record ? 'Edit attendance' : 'Record attendance'} close={onClose}>
      <form onSubmit={submit}>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="form-grid">
          <label>Employee *<select required value={form.employee_id} onChange={set('employee_id')}><option value="">Select employee</option>
            {(emps?.items || []).map((x) => <option key={x.id} value={x.id}>{x.name} ({x.employee_code})</option>)}</select></label>
          <label>Date *<input required type="date" value={form.attendance_date} onChange={set('attendance_date')} /></label>
          <label>Status<select value={form.status} onChange={set('status')}>{STATUSES.map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>Check-in<input type="time" value={form.check_in} onChange={set('check_in')} /></label>
          <label>Check-out<input type="time" value={form.check_out} onChange={set('check_out')} /></label>
          <label className="wide-field">Notes<input maxLength={500} value={form.notes} onChange={set('notes')} /></label>
        </div>
        <div className="modal-actions"><button type="button" className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Save attendance'}</button></div>
      </form>
    </Modal>
  )
}
