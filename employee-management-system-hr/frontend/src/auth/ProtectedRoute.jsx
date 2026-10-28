import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

/** Client-side guard for UX only. The Flask API enforces the real permissions. */
export default function ProtectedRoute({ adminOnly = false }) {
  const { token, user, isAdmin } = useAuth()
  const location = useLocation()
  if (!token || !user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (user.must_change_password && location.pathname !== '/profile') return <Navigate to="/profile" replace />
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />
  return <Outlet />
}
