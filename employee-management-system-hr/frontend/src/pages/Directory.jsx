import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import api, { errorMessage } from '../api/client'
import useLoad from '../api/useLoad'
import { Empty, PageHeading, useToast } from '../components/ui'

function LookupPanel({ title, path, field, placeholder }) {
  const flash = useToast()
  const { data, error, reload } = useLoad(`/api/${path}`)
  const [value, setValue] = useState('')
  const add = async (e) => {
    e.preventDefault()
    try { await api.post(`/api/${path}`, { [field]: value }); setValue(''); flash(`${title.slice(0, -1)} added`); reload() } catch (err) { flash(errorMessage(err), 'error') }
  }
  const remove = async (id) => {
    try { await api.delete(`/api/${path}/${id}`); flash('Deleted'); reload() } catch (err) { flash(errorMessage(err), 'error') }
  }
  return (
    <section className="panel">
      <div className="panel-head"><div><h2>{title}</h2><p>Used as suggestions when adding employees</p></div></div>
      <form className="inline-form" onSubmit={add}>
        <input required maxLength={100} placeholder={placeholder} aria-label={placeholder} value={value} onChange={(e) => setValue(e.target.value)} />
        <button className="btn primary"><Plus size={15} /> Add</button>
      </form>
      {error && <div className="form-error" role="alert">{error}</div>}
      <ul className="chip-list">
        {(data?.items || []).map((r) => <li key={r.id}>{r[field]}<button className="icon-btn danger-text" aria-label={`Delete ${r[field]}`} onClick={() => remove(r.id)}><Trash2 size={14} /></button></li>)}
        {data && !data.items.length && <Empty text="Nothing here yet." />}
      </ul>
    </section>
  )
}

export default function Directory() {
  return (
    <>
      <PageHeading kicker="ORGANISATION" title="Departments & designations" subtitle="Entries that are assigned to employees cannot be deleted." />
      <div className="two-col">
        <LookupPanel title="Departments" path="departments" field="name" placeholder="New department name" />
        <LookupPanel title="Designations" path="designations" field="title" placeholder="New designation title" />
      </div>
    </>
  )
}
