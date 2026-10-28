import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Employees from './pages/Employees'
import Attendance from './pages/Attendance'
import Salary from './pages/Salary'
import Leaves from './pages/Leaves'
import Directory from './pages/Directory'
import Reports from './pages/Reports'
import Profile from './pages/Profile'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="employees" element={<Employees />} />
          <Route path="attendance" element={<Attendance />} />
          <Route path="salary" element={<Salary />} />
          <Route path="leaves" element={<Leaves />} />
          <Route path="profile" element={<Profile />} />
          <Route element={<ProtectedRoute adminOnly />}>
            <Route path="directory" element={<Directory />} />
            <Route path="reports" element={<Reports />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
