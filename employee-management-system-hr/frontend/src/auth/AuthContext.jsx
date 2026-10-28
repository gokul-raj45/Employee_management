import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api, { AUTH_EXPIRED_EVENT, TOKEN_KEY, USER_KEY } from '../api/client'

const AuthContext = createContext(null)
export const useAuth = () => useContext(AuthContext)

function readUser() {
  try { return JSON.parse(sessionStorage.getItem(USER_KEY) || 'null') } catch { return null }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(readUser)
  const [expired, setExpired] = useState(false)

  const clear = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(USER_KEY)
    setToken(''); setUser(null)
  }, [])

  const persistUser = useCallback((u) => { sessionStorage.setItem(USER_KEY, JSON.stringify(u)); setUser(u) }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/api/login', { email, password })
    sessionStorage.setItem(TOKEN_KEY, data.access_token)
    persistUser(data.user); setToken(data.access_token); setExpired(false)
    return data.user
  }, [persistUser])

  const logout = useCallback(() => { setExpired(false); clear() }, [clear])

  // Token expired / account disabled -> back to login with a message.
  useEffect(() => {
    const onExpired = () => { setExpired(true); clear() }
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired)
  }, [clear])

  // Re-validate the stored token on page load so the UI never trusts stale sessionStorage.
  useEffect(() => {
    if (!token) return
    api.get('/api/me').then(({ data }) => persistUser({ id: data.id, username: data.username, email: data.email, role: data.role, must_change_password: data.must_change_password })).catch(() => {})
  }, [token, persistUser])

  const value = useMemo(() => ({ token, user, isAdmin: user?.role === 'admin', expired, login, logout, persistUser }),
    [token, user, expired, login, logout, persistUser])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
