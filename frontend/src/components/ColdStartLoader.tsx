import { useEffect, useState } from 'react'
import { getBackendWarmth, onBackendWarmthChange, type BackendWarmth } from '../lib/api'

/**
 * Cold-start loader banner.
 *
 * Shows a dismissible banner at the top of the page when the backend is
 * 'warming' (first request in flight) or 'cold' (a request timed out
 * and is being retried). Once 'warm', the banner disappears.
 *
 * The honest copy ("Waking up the Render free-tier container...") sets
 * judge expectations: yes there's a delay, we know about it, we're
 * handling it.
 */
export default function ColdStartLoader() {
  const [warmth, setWarmth] = useState<BackendWarmth>(getBackendWarmth())
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const unsub = onBackendWarmthChange(setWarmth)
    return unsub
  }, [])

  // Tick elapsed seconds while warming/cold to show progress
  useEffect(() => {
    if (warmth === 'warm' || warmth === 'unknown') {
      setElapsed(0)
      return
    }
    const start = Date.now()
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 200)
    return () => clearInterval(id)
  }, [warmth])

  if (warmth === 'warm' || warmth === 'unknown') return null

  const isCold = warmth === 'cold'
  const bgColor = isCold ? '#FEF3C7' : '#EFF6FF'
  const borderColor = isCold ? '#FDE68A' : '#BFDBFE'
  const textColor = isCold ? '#92400E' : '#1D4ED8'
  const dotColor = isCold ? '#D97706' : '#2563EB'

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0,
        background: bgColor,
        borderBottom: `1px solid ${borderColor}`,
        color: textColor,
        padding: '8px 24px',
        fontSize: 13,
        fontWeight: 500,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        zIndex: 9999,
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
      }}
    >
      <span
        style={{
          width: 8, height: 8, borderRadius: '50%',
          background: dotColor,
          animation: 'pulse 1.2s infinite',
          flexShrink: 0,
        }}
      />
      {isCold ? (
        <span>
          <strong>Backend still warming up</strong> — Render free-tier cold start in progress
          {elapsed > 0 && <span style={{ marginLeft: 8, opacity: 0.7 }}>({elapsed}s elapsed, retrying…)</span>}
        </span>
      ) : (
        <span>
          <strong>Waking up the backend</strong> — first request after inactivity takes ~30–60s on Render free tier
          {elapsed > 0 && <span style={{ marginLeft: 8, opacity: 0.7 }}>({elapsed}s)</span>}
        </span>
      )}
      <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.6 }}>
        Subsequent requests will be instant
      </span>
    </div>
  )
}
