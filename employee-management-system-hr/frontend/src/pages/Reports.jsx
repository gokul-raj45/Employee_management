import { useState } from 'react'
import useLoad from '../api/useLoad'
import { Empty, Loading, PageHeading, money } from '../components/ui'

export default function Reports() {
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7))
  const { data, loading, error } = useLoad('/api/reports/summary', { month })
  const { data: act } = useLoad('/api/activity', { limit: 50 })
  const rows = (obj) => Object.entries(obj || {})
  return (
    <>
      <PageHeading kicker="INSIGHTS" title="Reports & activity" subtitle="Monthly attendance, leave and payroll summary.">
        <label className="inline">Month <input type="month" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} /></label>
      </PageHeading>
      {error && <div className="form-error" role="alert">{error}</div>}
      {loading && !data ? <Loading /> : data && (
        <div className="stats">
          <div className="stat"><span>Payroll net total</span><strong>{money(data.payroll.total_net)}</strong><small>{data.payroll.records} salary records</small></div>
          <div className="stat"><span>Attendance</span>{rows(data.attendance).length ? rows(data.attendance).map(([k, v]) => <small key={k}>{k}: <b>{v}</b></small>) : <small>No records</small>}</div>
          <div className="stat"><span>Leave requests starting</span>{rows(data.leaves).length ? rows(data.leaves).map(([k, v]) => <small key={k}>{k}: <b>{v}</b></small>) : <small>No requests</small>}</div>
          <div className="stat"><span>Payroll status</span>{rows(data.payroll.by_status).length ? rows(data.payroll.by_status).map(([k, v]) => <small key={k}>{k}: <b>{v}</b></small>) : <small>No records</small>}</div>
        </div>)}
      <section className="panel">
        <div className="panel-head"><div><h2>Administrative activity</h2><p>Most recent 50 actions</p></div></div>
        <div className="table-wrap"><table>
          <thead><tr><th>WHEN</th><th>ADMIN</th><th>ACTION</th><th>DETAIL</th></tr></thead>
          <tbody>{(act?.items || []).map((a) => <tr key={a.id}><td>{new Date(a.created_at + 'Z').toLocaleString()}</td><td>{a.actor}</td><td><code>{a.action}</code></td><td>{a.detail}</td></tr>)}
            {act && !act.items.length && <tr><td colSpan={4}><Empty text="No activity recorded yet." /></td></tr>}</tbody></table></div>
      </section>
    </>
  )
}
