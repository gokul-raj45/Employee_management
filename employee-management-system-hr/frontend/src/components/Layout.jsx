import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { BarChart3, CalendarCheck, CalendarOff, FolderTree, LayoutDashboard, LogOut, Menu, ShieldCheck, UserCog, Users, Wallet, X } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  ['/', 'Dashboard', LayoutDashboard, false],
  ['/employees', 'Employee details', Users, false],
  ['/attendance', 'Attendance', CalendarCheck, false],
  ['/leaves', 'Leave requests', CalendarOff, false],
  ['/salary', 'Salary details', Wallet, false],
  ['/directory', 'Departments & roles', FolderTree, true],
  ['/reports', 'Reports & activity', BarChart3, true],
  ['/profile', 'Profile & password', UserCog, false],
]

export default function Layout() {
  const { user, isAdmin, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const items = NAV.filter(([, , , adminOnly]) => !adminOnly || isAdmin)
  const current = items.find(([to]) => (to === '/' ? pathname === '/' : pathname.startsWith(to)))

  const signOut = () => { logout(); navigate('/login') }

  return (
    <div className="layout">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand">
          <span className="logo-icon"><Users /></span>
          <span>PeopleDesk<small>HR MANAGEMENT</small></span>
          <button className="mobile-x icon-btn" onClick={() => setOpen(false)} aria-label="Close menu"><X /></button>
        </div>
        <div className="nav-caption">WORKSPACE</div>
        {items.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}
            className={({ isActive }) => `nav-link ${isActive ? 'selected' : ''}`}>
            <Icon size={18} />{label}
          </NavLink>
        ))}
        <div className="side-bottom">
          <div className="secure"><ShieldCheck size={18} />
            <div><b>{isAdmin ? 'Administrator' : 'Employee access'}</b><small>{isAdmin ? 'Can manage all HR records' : 'Own records only'}</small></div>
          </div>
          <button className="nav-link" onClick={signOut}><LogOut size={18} />Sign out</button>
        </div>
      </aside>
      {open && <button className="scrim" onClick={() => setOpen(false)} aria-label="Close menu" />}
      <main className="main">
        <header className="topbar">
          <button className="menu-btn icon-btn" onClick={() => setOpen(true)} aria-label="Open menu"><Menu /></button>
          <div className="breadcrumb">PeopleDesk <span>/</span> {current?.[1]}</div>
          <div className="top-user">
            <span className="live-dot" /><span className="live-label">Secure session</span>
            <div className="user-avatar">{(user?.username || 'U')[0].toUpperCase()}</div>
            <div><b>{user?.username}</b><small>{isAdmin ? 'Administrator' : 'Employee'}</small></div>
          </div>
        </header>
        <div className="content"><Outlet /></div>
        <footer>PeopleDesk HR <span>React · Flask · PostgreSQL · Role-based access</span></footer>
      </main>
    </div>
  )
}
