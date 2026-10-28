// Unit tests for client-side route guards (no network). The API enforces real permissions; see backend tests.
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import ProtectedRoute from '../auth/ProtectedRoute'
import { TOKEN_KEY, USER_KEY, errorMessage } from '../api/client'

const setSession = (user) => { sessionStorage.setItem(TOKEN_KEY, 't'); sessionStorage.setItem(USER_KEY, JSON.stringify(user)) }
const renderAt = (path) => render(
  <MemoryRouter initialEntries={[path]}><AuthProvider>
    <Routes>
      <Route path="/login" element={<div>LOGIN PAGE</div>} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<div>HOME</div>} /><Route path="/profile" element={<div>PROFILE</div>} />
        <Route element={<ProtectedRoute adminOnly />}><Route path="/reports" element={<div>ADMIN ONLY</div>} /></Route>
      </Route>
    </Routes>
  </AuthProvider></MemoryRouter>)

beforeEach(() => sessionStorage.clear())

describe('ProtectedRoute', () => {
  it('redirects anonymous visitors to /login', () => { renderAt('/'); expect(screen.getByText('LOGIN PAGE')).toBeInTheDocument() })
  it('lets a signed-in employee in', () => { setSession({ id: 2, username: 'a', role: 'employee' }); renderAt('/'); expect(screen.getByText('HOME')).toBeInTheDocument() })
  it('keeps employees out of admin routes', () => { setSession({ id: 2, username: 'a', role: 'employee' }); renderAt('/reports'); expect(screen.queryByText('ADMIN ONLY')).toBeNull(); expect(screen.getByText('HOME')).toBeInTheDocument() })
  it('lets admins into admin routes', () => { setSession({ id: 1, username: 'x', role: 'admin' }); renderAt('/reports'); expect(screen.getByText('ADMIN ONLY')).toBeInTheDocument() })
  it('forces a temporary-password change first', () => { setSession({ id: 2, username: 'a', role: 'employee', must_change_password: true }); renderAt('/'); expect(screen.getByText('PROFILE')).toBeInTheDocument() })
})

describe('errorMessage', () => {
  it('uses the API error field', () => expect(errorMessage({ response: { status: 409, data: { error: 'Duplicate' } } })).toBe('Duplicate'))
  it('explains network/CORS failures', () => expect(errorMessage({ message: 'Network Error' })).toMatch(/Cannot reach the server/))
})
