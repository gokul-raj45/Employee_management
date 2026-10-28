import { useCallback, useEffect, useRef, useState } from 'react'
import api, { errorMessage } from './client'

/** GET `url` (with optional params); returns { data, loading, error, reload }. Ignores stale responses. */
export default function useLoad(url, params) {
  const [state, setState] = useState({ data: null, loading: true, error: '' })
  const seq = useRef(0)
  const key = JSON.stringify(params || {})
  const load = useCallback(async () => {
    const mine = ++seq.current
    setState((s) => ({ ...s, loading: true, error: '' }))
    try {
      const { data } = await api.get(url, { params: JSON.parse(key) })
      if (mine === seq.current) setState({ data, loading: false, error: '' })
    } catch (e) {
      if (mine === seq.current) setState({ data: null, loading: false, error: errorMessage(e) })
    }
  }, [url, key])
  useEffect(() => { load() }, [load])
  return { ...state, reload: load }
}
