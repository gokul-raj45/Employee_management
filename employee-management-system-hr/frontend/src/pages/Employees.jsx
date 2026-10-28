import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Download, Edit3, Plus, Power, Search, Trash2 } from 'lucide-react'
import api, { errorMessage } from '../api/client'
import useLoad from '../api/useLoad'
import { useAuth } from '../auth/AuthContext'
import { ConfirmDialog, Empty, Loading, Modal, PageHeading, Status, useToast } from '../components/ui'

const BLANK = { employee_code: '', name: '', email: '', phone: '', department: '', designation: '', employment_type: 'Full-time',
  status: 'Active', joining_date: '', location: '', notes: '', initial_password: '' }

export default function Employees() {
  const { isAdmin } = useAuth()
  const flash = useToast()
  const [filters, setFilters] = useState({ search: '', department: '', status: '' })
  const [debounced, setDebounced] = useState(filters.search)
  const [page, setPage] = useState(1)
  const [modal, setModal] = useState(null)       // null | {employee|null}
  const [confirm, setConfirm] = useState(null)   // {kind, employee}

  useEffect(() => { const t = setTimeout(() => setDebounced(filters.search), 300); return () => clearTimeout(t) }, [filters.search])
  useEffect(() => { setPage(1) }, [debounced, filters.department, filters.status])

  const { data, loading, error, reload } = useLoad('/api/employees', { search: debounced, department: filters.department, status: filters.status, page, per_page: 10 })
  const deptNames = data?.departments || []

  const exportCsv = async () => {
    try {
      const { data: blob } = await api.get('/api/employees/export.csv', { responseType: 'blob' })
      const url = URL.createObjectURL(blob); const a = document.createElement('a')
      a.href = url; a.download = 'employees.csv'; a.click(); URL.revokeObjectURL(url)
    } catch (e) { flash(errorMessage(e), 'error') }
  }

  const runConfirm = async () => {
    const { kind, employee } = confirm
    try {
      if (kind === 'delete') await api.delete(`/api/employees/${employee.id}`)
      else await api.post(`/api/employees/${employee.id}/${kind}`)
      flash(kind === 'delete' ? 'Employee deleted' : kind === 'deactivate' ? 'Employee deactivated' : 'Employee reactivated')
      setConfirm(null); reload()
    } catch (e) { flash(errorMessage(e), 'error'); setConfirm(null) }
  }

  const items = data?.items || []
  return (
    <>
      <PageHeading kicker="PEOPLE DIRECTORY" title={isAdmin ? 'Employee details' : 'My employee details'}
        subtitle={isAdmin ? 'Create, search, update and deactivate employee records.' : 'Your own employee record.'}>
        {isAdmin && <>
          <button className="btn secondary" onClick={exportCsv}><Download size={16} /> Export CSV</button>
          <button className="btn primary" onClick={() => setModal({ employee: null })}><Plus size={16} /> Add employee</button>
        </>}
      </PageHeading>
      <section className="panel">
        <div className="toolbar">
          <div className="search"><Search size={16} />
            <input placeholder="Search employee details…" aria-label="Search" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} /></div>
          {isAdmin && (
            <div className="filters">
              <select aria-label="Department filter" value={filters.department} onChange={(e) => setFilters({ ...filters, department: e.target.value })}>
                <option value="">All departments</option>{deptNames.map((d) => <option key={d}>{d}</option>)}</select>
              <select aria-label="Status filter" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
                <option value="">All statuses</option><option>Active</option><option>On Leave</option><option>Inactive</option></select>
            </div>
          )}
        </div>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="table-wrap">
          <table>
            <thead><tr><th>EMPLOYEE</th><th>CODE</th><th>DEPARTMENT / ROLE</th><th>TYPE</th><th>STATUS</th><th>JOINED</th>{isAdmin && <th>ACTIONS</th>}</tr></thead>
            <tbody>
              {loading && !data ? <tr><td colSpan={7}><Loading /></td></tr> : items.map((e) => (
                <tr key={e.id}>
                  <td><b>{e.name}</b><small className="sub">{e.email}</small></td>
                  <td><code>{e.employee_code}</code></td>
                  <td><b>{e.department}</b><small className="sub">{e.designation}</small></td>
                  <td>{e.employment_type}</td><td><Status status={e.status} /></td><td>{e.joining_date || '—'}</td>
                  {isAdmin && <td>
                    <button className="icon-btn" title="Edit" aria-label={`Edit ${e.name}`} onClick={() => setModal({ employee: e })}><Edit3 size={16} /></button>
                    <button className="icon-btn" title={e.status === 'Inactive' ? 'Reactivate' : 'Deactivate'} aria-label={`${e.status === 'Inactive' ? 'Reactivate' : 'Deactivate'} ${e.name}`}
                      onClick={() => setConfirm({ kind: e.status === 'Inactive' ? 'activate' : 'deactivate', employee: e })}><Power size={16} /></button>
                    <button className="icon-btn danger-text" title="Delete permanently" aria-label={`Delete ${e.name}`} onClick={() => setConfirm({ kind: 'delete', employee: e })}><Trash2 size={16} /></button>
                  </td>}
                </tr>
              ))}
              {!loading && !items.length && <tr><td colSpan={isAdmin ? 7 : 6}><Empty text="No employee records found." /></td></tr>}
            </tbody>
          </table>
        </div>
        {isAdmin && data && (
          <div className="pagination"><span>{data.total} records · Page {page} of {Math.max(1, data.pages)}</span>
            <div><button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft size={15} /> Previous</button>
              <button className="btn secondary" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>Next <ChevronRight size={15} /></button></div></div>
        )}
      </section>
      {modal && isAdmin && <EmployeeForm employee={modal.employee} departments={deptNames} onClose={() => setModal(null)} onSaved={() => { setModal(null); reload() }} />}
      {confirm && <ConfirmDialog
        title={confirm.kind === 'delete' ? 'Delete permanently?' : confirm.kind === 'deactivate' ? 'Deactivate employee?' : 'Reactivate employee?'}
        text={confirm.kind === 'delete' ? `${confirm.employee.name} and ALL their attendance, salary and leave records will be removed. Consider deactivating instead.`
          : confirm.kind === 'deactivate' ? `${confirm.employee.name} will no longer be able to sign in. Their records are kept.` : `${confirm.employee.name} will be able to sign in again.`}
        confirmLabel={confirm.kind === 'delete' ? 'Delete' : 'Confirm'} onConfirm={runConfirm} onCancel={() => setConfirm(null)} />}
    </>
  )
}

function EmployeeForm({ employee, departments, onClose, onSaved }) {
  const flash = useToast()
  const [form, setForm] = useState(employee ? { ...BLANK, ...employee, initial_password: '' } : { ...BLANK, department: departments[0] || '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { data: desig } = useLoad('/api/designations')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    const body = { ...form, joining_date: form.joining_date || null }
    if (employee || !body.initial_password) delete body.initial_password
    try {
      if (employee) await api.put(`/api/employees/${employee.id}`, body); else await api.post('/api/employees', body)
      flash(employee ? 'Employee updated' : 'Employee created'); onSaved()
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }

  return (
    <Modal title={employee ? 'Edit employee' : 'Add employee'} close={onClose}>
      <form onSubmit={submit}>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="form-grid">
          <label>Full name *<input required value={form.name} onChange={set('name')} /></label>
          <label>Work email *<input required type="email" value={form.email} onChange={set('email')} /></label>
          <label>Employee code<input value={form.employee_code} onChange={set('employee_code')} placeholder="Auto-generated if empty" /></label>
          <label>Phone<input value={form.phone || ''} onChange={set('phone')} /></label>
          <label>Department *<input required list="dept-list" value={form.department} onChange={set('department')} /></label>
          <label>Designation *<input required list="desig-list" value={form.designation} onChange={set('designation')} /></label>
          <label>Employment type<select value={form.employment_type} onChange={set('employment_type')}>{['Full-time', 'Part-time', 'Contract', 'Intern'].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>Status<select value={form.status} onChange={set('status')}>{['Active', 'On Leave', 'Inactive'].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>Joining date<input type="date" value={form.joining_date || ''} onChange={set('joining_date')} /></label>
          <label>Location<input value={form.location || ''} onChange={set('location')} /></label>
          {!employee && <label className="wide-field">Initial password (optional — creates a login the employee must change at first sign-in)
            <input type="password" autoComplete="new-password" minLength={8} value={form.initial_password} onChange={set('initial_password')} /></label>}
          <label className="wide-field">Notes<textarea value={form.notes || ''} onChange={set('notes')} /></label>
        </div>
        <datalist id="dept-list">{departments.map((d) => <option key={d} value={d} />)}</datalist>
        <datalist id="desig-list">{(desig?.items || []).map((d) => <option key={d.id} value={d.title} />)}</datalist>
        <div className="modal-actions"><button type="button" className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Save employee'}</button></div>
      </form>
    </Modal>
  )
}
