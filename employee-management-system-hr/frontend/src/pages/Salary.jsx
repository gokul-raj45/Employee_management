import { useState } from 'react'
import { Edit3, FileText, LockKeyhole, Plus, Printer, Trash2 } from 'lucide-react'
import api, { errorMessage } from '../api/client'
import useLoad from '../api/useLoad'
import { useAuth } from '../auth/AuthContext'
import { ConfirmDialog, Empty, Loading, Modal, PageHeading, Status, money, useToast } from '../components/ui'

export default function Salary() {
  const { isAdmin } = useAuth()
  const flash = useToast()
  const { data, loading, error, reload } = useLoad('/api/salaries')
  const [modal, setModal] = useState(null)
  const [del, setDel] = useState(null)
  const [slipId, setSlipId] = useState(null)
  const items = data?.items || []
  const remove = async () => {
    try { await api.delete(`/api/salaries/${del.id}`); flash('Salary record deleted'); setDel(null); reload() }
    catch (e) { flash(errorMessage(e), 'error'); setDel(null) }
  }
  return (
    <>
      <PageHeading kicker="PAYROLL" title="Salary details" subtitle={isAdmin ? 'Manage monthly salary records.' : 'Your own salary history and payslips.'}>
        {isAdmin && <button className="btn primary" onClick={() => setModal({ record: null })}><Plus size={16} /> Add salary record</button>}
      </PageHeading>
      <section className="panel">
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="table-wrap"><table>
          <thead><tr><th>EMPLOYEE</th><th>MONTH</th><th>BASIC</th><th>ALLOWANCES</th><th>BONUS</th><th>DEDUCTIONS</th><th>NET SALARY</th><th>PAYMENT</th><th>ACTIONS</th></tr></thead>
          <tbody>
            {loading && !data ? <tr><td colSpan={9}><Loading /></td></tr> : items.map((s) => (
              <tr key={s.id}>
                <td><b>{s.employee_name}</b><small className="sub">{s.employee_code}</small></td><td>{s.pay_month}</td><td>{money(s.basic_salary)}</td>
                <td>{money(s.allowances)}</td><td>{money(s.bonus)}</td><td>{money(s.deductions)}</td><td><b>{money(s.net_salary)}</b></td><td><Status status={s.payment_status} /></td>
                <td><button className="icon-btn" title="Payslip" aria-label="View payslip" onClick={() => setSlipId(s.id)}><FileText size={16} /></button>
                  {isAdmin && <><button className="icon-btn" aria-label="Edit salary" onClick={() => setModal({ record: s })}><Edit3 size={16} /></button>
                    <button className="icon-btn danger-text" aria-label="Delete salary" onClick={() => setDel(s)}><Trash2 size={16} /></button></>}</td>
              </tr>))}
            {!loading && !items.length && <tr><td colSpan={9}><Empty text="No salary records available." /></td></tr>}
          </tbody></table></div>
        <div className="salary-privacy"><LockKeyhole size={16} /> Employees can only view salary records linked to their account.</div>
      </section>
      {modal && isAdmin && <SalaryForm record={modal.record} onClose={() => setModal(null)} onSaved={() => { setModal(null); reload() }} />}
      {slipId && <Payslip id={slipId} onClose={() => setSlipId(null)} />}
      {del && <ConfirmDialog title="Delete this record?" text="This action cannot be undone." confirmLabel="Delete" onConfirm={remove} onCancel={() => setDel(null)} />}
    </>
  )
}

function Payslip({ id, onClose }) {
  const { data, error } = useLoad(`/api/salaries/${id}/payslip`)
  const p = data?.payslip
  return (
    <Modal title="Payslip" close={onClose}>
      {error && <div className="form-error" role="alert">{error}</div>}
      {p && <div className="payslip" id="payslip">
        <h3>{p.employee_name} <small>({p.employee_code})</small></h3>
        <p>{p.designation} · {p.department} — Pay period <b>{p.pay_month}</b></p>
        <table><tbody>
          <tr><td>Basic salary</td><td>{money(p.basic_salary)}</td></tr><tr><td>Allowances</td><td>{money(p.allowances)}</td></tr>
          <tr><td>Bonus</td><td>{money(p.bonus)}</td></tr><tr><th>Gross earnings</th><th>{money(p.gross_earnings)}</th></tr>
          <tr><td>Deductions</td><td>− {money(p.deductions)}</td></tr><tr className="net"><th>Net salary</th><th>{money(p.net_salary)}</th></tr>
        </tbody></table>
        <p>Payment: <Status status={p.payment_status} /> {p.paid_on && `on ${p.paid_on}`}</p>
        {p.notes && <p><small>{p.notes}</small></p>}
      </div>}
      <div className="modal-actions"><button className="btn secondary" onClick={() => window.print()}><Printer size={15} /> Print</button><button className="btn primary" onClick={onClose}>Close</button></div>
    </Modal>
  )
}

function SalaryForm({ record, onClose, onSaved }) {
  const flash = useToast()
  const { data: emps } = useLoad('/api/employees', { per_page: 100 })
  const [form, setForm] = useState(record ? { employee_id: String(record.employee_id), pay_month: record.pay_month, basic_salary: String(record.basic_salary), allowances: String(record.allowances),
    deductions: String(record.deductions), bonus: String(record.bonus), payment_status: record.payment_status, paid_on: record.paid_on || '', notes: record.notes }
    : { employee_id: '', pay_month: new Date().toISOString().slice(0, 7), basic_salary: '', allowances: '0', deductions: '0', bonus: '0', payment_status: 'Pending', paid_on: '', notes: '' })
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const net = Number(form.basic_salary || 0) + Number(form.allowances || 0) + Number(form.bonus || 0) - Number(form.deductions || 0)
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    try {
      const body = { ...form, employee_id: Number(form.employee_id), paid_on: form.paid_on || null }
      if (record) await api.put(`/api/salaries/${record.id}`, body); else await api.post('/api/salaries', body)
      flash('Salary record saved'); onSaved()
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }
  return (
    <Modal title={record ? 'Edit salary record' : 'Add salary record'} close={onClose}>
      <form onSubmit={submit}>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="form-grid">
          <label>Employee *<select required value={form.employee_id} onChange={set('employee_id')}><option value="">Select employee</option>
            {(emps?.items || []).map((x) => <option key={x.id} value={x.id}>{x.name} ({x.employee_code})</option>)}</select></label>
          <label>Pay month *<input required type="month" value={form.pay_month} onChange={set('pay_month')} /></label>
          {[['basic_salary', 'Basic salary'], ['allowances', 'Allowances'], ['bonus', 'Bonus'], ['deductions', 'Deductions']].map(([k, l]) => (
            <label key={k}>{l} (₹)<input required type="number" min="0" step=".01" value={form[k]} onChange={set(k)} /></label>))}
          <label>Payment status<select value={form.payment_status} onChange={set('payment_status')}>{['Pending', 'Paid', 'On Hold'].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>Paid on<input type="date" value={form.paid_on} onChange={set('paid_on')} /></label>
          <label className="wide-field">Notes<input maxLength={500} value={form.notes} onChange={set('notes')} /></label>
        </div>
        <div className="salary-calc">Net salary preview: <b>{money(net)}</b></div>
        <div className="modal-actions"><button type="button" className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Save salary'}</button></div>
      </form>
    </Modal>
  )
}
