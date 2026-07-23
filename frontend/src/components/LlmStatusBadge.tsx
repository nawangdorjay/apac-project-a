import { useEffect, useState } from 'react'
import { getLlmStatus, LlmStatus } from '../lib/api'

/**
 * Live LLM tier badge — surfaces the 4-tier failover state.
 *
 * Polls /api/llm-status every 5s while mounted. Shows:
 *   - Which tier answered the most recent call (Gemini / NIM / Ollama / Mock)
 *   - Whether the circuit breaker is active (Gemini blocked for X more seconds)
 *   - Cache size + RPM usage as a tooltip
 *
 * Judges can SEE the failover happening in real time, which is the whole
 * point of the 4-tier architecture.
 */
export default function LlmStatusBadge({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<LlmStatus | null>(null)
  const [error, setError] = useState(false)

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
  const tooltip = [
    `Model: ${status.model}`,
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
        background: cb.active ? '#FEF3C7' : `${tier.color}15`,
        color: cb.active ? '#92400E' : tier.color,
        fontSize: 11, fontWeight: 700, border: `1px solid ${cb.active ? '#FDE68A' : `${tier.color}40`}`,
        cursor: 'help',
        transition: 'all 0.3s',
      }}
    >
      <span
        style={{
          width: 6, height: 6, borderRadius: '50%',
          background: cb.active ? '#D97706' : tier.color,
          animation: 'pulse 2s infinite',
        }}
      />
      <span>{tier.icon}</span>
      {!compact && <span>{tier.label}</span>}
      {cb.active && !compact && (
        <span style={{ fontSize: 10, opacity: 0.8 }}>({cb.remaining_sec}s)</span>
      )}
    </span>
  )
}
