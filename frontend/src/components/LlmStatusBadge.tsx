import { useEffect, useState } from 'react'
import { getLlmStatus, getBackendWarmth, onBackendWarmthChange, LlmStatus, BackendWarmth } from '../lib/api'

/**
 * Live LLM tier badge — surfaces the 4-tier failover state AND the
 * backend cold-start state.
 *
 * Polls /api/llm-status every 5s while mounted. Shows:
 *   - Which tier answered the most recent call (Gemini / NIM / Ollama / Mock)
 *   - Whether the circuit breaker is active (Gemini blocked for X more seconds)
 *   - Whether the backend is cold-starting (amber "warming" pulse)
 *   - Cache size + RPM usage as a tooltip
 *
 * Judges can SEE the failover happening in real time, which is the whole
 * point of the 4-tier architecture.
 */
export default function LlmStatusBadge({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<LlmStatus | null>(null)
  const [warmth, setWarmth] = useState<BackendWarmth>(getBackendWarmth())
  const [error, setError] = useState(false)

  useEffect(() => {
    const unsub = onBackendWarmthChange(setWarmth)
    return unsub
  }, [])

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const s = await getLlmStatus()
        if (!cancelled) {
          setStatus(s)
          setError(false)
        }
      } catch {
        if (!cancelled) setError(true)
      }
    }
    poll()
    const id = setInterval(poll, 5000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  // Cold-start state takes precedence — if backend is warming, show that
  const isColdStarting = warmth === 'warming' || warmth === 'cold'

  if (isColdStarting && !status) {
    // Backend hasn't responded yet AND we know it's cold — show cold-start state
    return (
      <span
        title="Backend is waking up (Render free-tier cold start)"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 10px', borderRadius: 20,
          background: warmth === 'cold' ? '#FEF3C7' : '#EFF6FF',
          color: warmth === 'cold' ? '#92400E' : '#1D4ED8',
          fontSize: 11, fontWeight: 700,
          border: `1px solid ${warmth === 'cold' ? '#FDE68A' : '#BFDBFE'}`,
        }}
      >
        <span
          style={{
            width: 6, height: 6, borderRadius: '50%',
            background: warmth === 'cold' ? '#D97706' : '#2563EB',
            animation: 'pulse 1.2s infinite',
          }}
        />
        {!compact && <span>{warmth === 'cold' ? 'Backend cold — retrying' : 'Waking backend…'}</span>}
        {compact && <span>{warmth === 'cold' ? 'Cold' : 'Warming'}</span>}
      </span>
    )
  }

  if (error || !status) {
    return (
      <span
        title="LLM status unavailable"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 10px', borderRadius: 20,
          background: '#F1F5F9', color: '#94A3B8',
          fontSize: 11, fontWeight: 600, border: '1px solid #E2E8F0',
        }}
      >
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#94A3B8' }} />
        {compact ? 'LLM …' : 'LLM status …'}
      </span>
    )
  }

  const tier = status.last_tier_used
  const cb = status.circuit_breaker

  // If circuit breaker is active OR backend is cold-starting, show amber
  const isAmber = cb.active || isColdStarting
  const amberColor = '#D97706'
  const activeColor = isAmber ? amberColor : tier.color
  const activeBg = isAmber ? '#FEF3C7' : `${tier.color}15`
  const activeBorder = isAmber ? '#FDE68A' : `${tier.color}40`

  const tooltip = [
    `Model: ${status.model}`,
    `Backend: ${warmth}`,
    `Last tier: ${tier.label}`,
    `Cache entries: ${status.cache_entries}`,
    `Calls last minute: ${status.calls_last_minute} / ${status.rpm_limit} RPM`,
    `Circuit breaker: ${cb.active ? `ACTIVE (${cb.remaining_sec}s remaining)` : 'inactive'}`,
    '',
    'Configured tiers:',
    ...status.tiers.map(t => `  ${t.active ? '✓' : '✗'} ${t.name} (${t.type})`),
  ].join('\n')

  return (
    <span
      title={tooltip}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '4px 10px', borderRadius: 20,
        background: activeBg,
        color: activeColor,
        fontSize: 11, fontWeight: 700, border: `1px solid ${activeBorder}`,
        cursor: 'help',
        transition: 'all 0.3s',
      }}
    >
      <span
        style={{
          width: 6, height: 6, borderRadius: '50%',
          background: activeColor,
          animation: 'pulse 2s infinite',
        }}
      />
      <span>{tier.icon}</span>
      {!compact && <span>{tier.label}</span>}
      {cb.active && !compact && (
        <span style={{ fontSize: 10, opacity: 0.8 }}>(CB {cb.remaining_sec}s)</span>
      )}
      {isColdStarting && !cb.active && !compact && (
        <span style={{ fontSize: 10, opacity: 0.8 }}>(warming)</span>
      )}
    </span>
  )
}

