import { Link } from 'react-router-dom'
import { CalendarCheck, CalendarOff, LockKeyhole, ShieldCheck, Users, Wallet } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import useLoad from '../api/useLoad'
import { Empty, Loading, PageHeading } from '../components/ui'

const Stat = ({ icon: I, tone, label, value, hint }) => (
  <div className="stat"><div className={`stat-icon ${tone}`}><I /></div><span>{label}</span><strong>{value ?? '—'}</strong><small>{hint}</small></div>
)

export default function Dashboard() {
  const { user, isAdmin } = useAuth()
  const { data, loading, error } = useLoad('/api/dashboard')
  if (loading && !data) return <Loading />
  if (error) return <div className="form-error" role="alert">{error}</div>
  return (
    <>
      <PageHeading kicker="OVERVIEW" title={`Hello, ${user.username} 👋`}
        subtitle={isAdmin ? 'Current overview of your workforce.' : 'Your employee details, attendance, leave and salary records.'} />
      {isAdmin ? <AdminView d={data} /> : <EmployeeView d={data} />}
    </>
  )
}

function AdminView({ d }) {
  const att = d.attendance_today || {}
  return (
    <>
      <div className="stats">
        <Stat icon={Users} tone="violet" label="Total employees" value={d.total} hint="All records" />
        <Stat icon={ShieldCheck} tone="green" label="Active" value={d.active} hint={`${d.inactive} inactive`} />
        <Stat icon={CalendarOff} tone="amber" label="Pending leave requests" value={d.pending_leaves} hint="Awaiting review" />
        <Stat icon={CalendarCheck} tone="blue" label="Present today" value={(att.Present || 0) + (att.Late || 0)} hint={`${att.Absent || 0} absent · ${att.Leave || 0} on leave`} />
      </div>
      <div className="two-col">
        <section className="panel">
          <div className="panel-head"><div><h2>Department overview</h2><p>Employee count by department</p></div></div>
          <div className="dept-list">
            {d.by_department.length ? d.by_department.map((x) => (
              <div key={x.department} className="dept-row"><span>{x.department}</span>
                <div className="track"><i style={{ width: `${Math.max(4, (x.count / Math.max(d.total, 1)) * 100)}%` }} /></div><b>{x.count}</b></div>
            )) : <Empty text="No employee records yet." />}
          </div>
        </section>
        <section className="panel">
          <div className="panel-head"><div><h2>Recent activity</h2><p>Latest administrative actions</p></div><Link className="link" to="/reports">View all</Link></div>
          <ul className="activity">
            {d.recent_activity.length ? d.recent_activity.map((a) => (
              <li key={a.id}><b>{a.actor}</b> <code>{a.action}</code> <span>{a.detail}</span><small>{new Date(a.created_at + 'Z').toLocaleString()}</small></li>
            )) : <Empty text="No activity yet." />}
          </ul>
        </section>
      </div>
    </>
  )
}

function EmployeeView({ d }) {
  const e = d.employee
  return (
    <>
      <div className="stats">
        <Stat icon={Users} tone="violet" label="My employee ID" value={e?.employee_code || 'Not linked'} hint="Contact admin if missing" />
        <Stat icon={CalendarCheck} tone="green" label="Attendance records" value={d.attendance_count} hint="Recorded by admin" />
        <Stat icon={CalendarOff} tone="amber" label="Pending leave requests" value={d.leave_pending} hint="Awaiting review" />
        <Stat icon={Wallet} tone="blue" label="Salary records" value={d.salary_count} hint="Private to your account" />
      </div>
      <section className="panel">
        <div className="panel-head"><div><h2>My employee details</h2><p>Contact details can be changed under Profile; other fields by an administrator.</p></div><LockKeyhole /></div>
        {e ? (
          <div className="profile-grid">
            {[['Full name', e.name], ['Employee code', e.employee_code], ['Email', e.email], ['Phone', e.phone], ['Department', e.department],
              ['Designation', e.designation], ['Employment type', e.employment_type], ['Status', e.status], ['Joining date', e.joining_date], ['Location', e.location]]
              .map(([k, v]) => <div key={k}><small>{k}</small><b>{v || '—'}</b></div>)}
          </div>
        ) : <Empty text="Your account is not linked to an employee record. Ask an administrator." />}
      </section>
    </>
  )
}
