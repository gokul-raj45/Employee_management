import { useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Users } from 'lucide-react'
import api, { errorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ui'

export default function Login() {
  const { token, user, expired, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const flash = useToast()
  const [mode, setMode] = useState('login')
  const [allowRegister, setAllowRegister] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { api.get('/api/auth/config').then(({ data }) => setAllowRegister(!!data.self_registration)).catch(() => {}) }, [])

  if (token && user) return <Navigate to={location.state?.from || '/'} replace />

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    try {
      if (mode === 'login') {
        await login(form.email, form.password)
        navigate(location.state?.from || '/', { replace: true })
      } else {
        await api.post('/api/register', form)
        flash('Account created. An administrator must link it to your employee record.')
        setMode('login')
      }
    } catch (err) {
      setError(errorMessage(err))
    } finally { setBusy(false) }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-logo"><span className="logo-icon"><Users /></span>PeopleDesk <small>HR MANAGEMENT</small></div>
      <form className="auth-card" onSubmit={submit} noValidate={false}>
        <div className="kicker">SECURE EMPLOYEE PORTAL</div>
        <h1>{mode === 'login' ? 'Welcome back' : 'Create employee account'}</h1>
        <p>Sign in with the account your administrator created for you.</p>
        {expired && mode === 'login' && <div className="form-error" role="alert">Your session expired. Please sign in again.</div>}
        {error && <div className="form-error" role="alert">{error}</div>}
        {mode === 'register' && <label>Username<input required minLength={3} value={form.username} onChange={set('username')} /></label>}
        <label>Email<input required type="email" autoComplete="username" value={form.email} onChange={set('email')} placeholder="you@company.com" /></label>
        <label>Password<input required minLength={8} type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={form.password} onChange={set('password')} /></label>
        <button className="btn primary wide" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
        {allowRegister && (
          <div className="auth-switch">{mode === 'login' ? 'Need an account?' : 'Already registered?'}{' '}
            <button type="button" className="link" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Register' : 'Sign in'}</button>
          </div>
        )}
      </form>
    </div>
  )
}
