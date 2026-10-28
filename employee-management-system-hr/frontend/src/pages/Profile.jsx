import { useState } from 'react'
import api, { errorMessage } from '../api/client'
import useLoad from '../api/useLoad'
import { useAuth } from '../auth/AuthContext'
import { Loading, PageHeading, useToast } from '../components/ui'

export default function Profile() {
  const { user, persistUser } = useAuth()
  const flash = useToast()
  const { data: me, loading, reload } = useLoad('/api/me')
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwError, setPwError] = useState('')
  const [contact, setContact] = useState(null)
  const emp = me?.employee
  const c = contact || { phone: emp?.phone || '', location: emp?.location || '' }

  const saveContact = async (e) => {
    e.preventDefault()
    try { await api.put('/api/me/profile', c); flash('Profile updated'); setContact(null); reload() } catch (err) { flash(errorMessage(err), 'error') }
  }
  const changePassword = async (e) => {
    e.preventDefault(); setPwError('')
    if (pw.new_password !== pw.confirm) return setPwError('New password and confirmation do not match')
    try {
      const { data } = await api.post('/api/change-password', { current_password: pw.current_password, new_password: pw.new_password })
      persistUser({ ...user, must_change_password: data.user.must_change_password })
      setPw({ current_password: '', new_password: '', confirm: '' }); flash('Password changed')
    } catch (err) { setPwError(errorMessage(err)) }
  }

  if (loading && !me) return <Loading />
  return (
    <>
      <PageHeading kicker="ACCOUNT" title="Profile & password" subtitle="Update your contact details and change your password." />
      {user.must_change_password && <div className="form-error" role="alert">You must change your temporary password before continuing.</div>}
      <div className="two-col">
        <section className="panel pad">
          <h2>Contact details</h2>
          {emp ? (
            <form onSubmit={saveContact}>
              <div className="profile-grid">{[['Name', emp.name], ['Employee code', emp.employee_code], ['Email', emp.email], ['Department', emp.department], ['Designation', emp.designation]]
                .map(([k, v]) => <div key={k}><small>{k}</small><b>{v}</b></div>)}</div>
              <div className="form-grid">
                <label>Phone<input maxLength={30} value={c.phone} onChange={(e) => setContact({ ...c, phone: e.target.value })} /></label>
                <label>Location<input maxLength={100} value={c.location} onChange={(e) => setContact({ ...c, location: e.target.value })} /></label>
              </div>
              <div className="modal-actions"><button className="btn primary">Save contact details</button></div>
            </form>
          ) : <p className="muted">{me?.role === 'admin' ? 'Administrator accounts have no employee profile.' : 'Your account is not linked to an employee record yet.'}</p>}
        </section>
        <section className="panel pad">
          <h2>Change password</h2>
          <form onSubmit={changePassword}>
            {pwError && <div className="form-error" role="alert">{pwError}</div>}
            <div className="form-grid single">
              <label>Current password<input required type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></label>
              <label>New password (min 8 characters)<input required minLength={8} maxLength={72} type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></label>
              <label>Confirm new password<input required type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></label>
            </div>
            <div className="modal-actions"><button className="btn primary">Change password</button></div>
          </form>
        </section>
      </div>
    </>
  )
}
