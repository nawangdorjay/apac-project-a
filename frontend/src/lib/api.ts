import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { DatasetContext } from '../store/pipelineStore'

const BASE_URL = import.meta.env.VITE_API_URL || ''

// Cold-start aware axios client.
//
// Render free-tier containers sleep after ~15 min of inactivity. The first
// request after sleep takes 30-60s to respond while uvicorn boots. We handle
// this by:
//   1. Setting a long initial timeout (90s) on every request
//   2. Tracking whether we've seen a "warm" response yet this session
//   3. Surfacing cold-start state via a global event the UI can subscribe to
//
// Once the backend is warm, subsequent requests use the normal fast path.

export type BackendWarmth = 'unknown' | 'cold' | 'warming' | 'warm'
let _warmth: BackendWarmth = 'unknown'
const _warmthListeners = new Set<(w: BackendWarmth) => void>()

export function getBackendWarmth(): BackendWarmth { return _warmth }

export function onBackendWarmthChange(cb: (w: BackendWarmth) => void): () => void {
  _warmthListeners.add(cb)
  return () => _warmthListeners.delete(cb)
}

function setWarmth(w: BackendWarmth) {
  if (_warmth !== w) {
    _warmth = w
    _warmthListeners.forEach(cb => cb(w))
  }
}

// Long timeout for cold-start tolerance. Most warm requests finish in <2s.
const COLD_START_TIMEOUT = 90000  // 90 seconds
const WARM_TIMEOUT = 30000        // 30 seconds (normal)

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: COLD_START_TIMEOUT,
})

// Cold-start wrapper: retry once on network error / timeout, with
// progress callbacks via the warmth listener.
async function coldStartRequest<T>(
  config: AxiosRequestConfig,
  opts: { retryOnTimeout?: boolean } = {}
): Promise<T> {
  const isInitialCold = _warmth === 'unknown' || _warmth === 'cold'
  if (isInitialCold) setWarmth('warming')

  const timeout = _warmth === 'warm' ? WARM_TIMEOUT : COLD_START_TIMEOUT
  const start = Date.now()

  try {
    const res: AxiosResponse<T> = await api.request<T>({ ...config, timeout })
    const elapsed = Date.now() - start

    // If first call took > 5s, we likely just woke the backend
    if (_warmth !== 'warm') {
      if (elapsed > 5000) {
        console.info(`[api] Backend responded in ${elapsed}ms — was likely cold, now warm`)
      }
      setWarmth('warm')
    }
    return res.data
  } catch (err: any) {
    // If we timed out and haven't retried yet, the backend is probably
    // still booting. Wait 3s and retry once with the long timeout.
    if (opts.retryOnTimeout !== false && _warmth !== 'warm') {
      const isTimeout = err.code === 'ECONNABORTED' || err.message?.includes('timeout')
      const isNetwork = err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')
      if (isTimeout || isNetwork) {
        console.warn(`[api] Cold-start retry: ${err.code || err.message} — waiting 3s and retrying once`)
        setWarmth('cold')
        await new Promise(r => setTimeout(r, 3000))
        return coldStartRequest<T>({ ...config, timeout: COLD_START_TIMEOUT }, { retryOnTimeout: false })
      }
    }
    throw err
  }
}

// Warmup helper — pings /api/warmup on Landing mount to pre-wake the
// backend before the user clicks anything. Non-blocking, fire-and-forget.
export async function warmupBackend(): Promise<void> {
  if (_warmth === 'warm') return
  try {
    setWarmth('warming')
    await coldStartRequest<{ ok: boolean; ts: number }>(
      { url: '/api/warmup', method: 'GET' },
      { retryOnTimeout: false }
    )
    setWarmth('warm')
  } catch (err) {
    // Don't crash — the user will see the cold-start loader on their first
    // real interaction. Warmth stays at 'cold' so the next request retries.
    setWarmth('cold')
    console.warn('[api] Warmup ping failed:', err)
  }
}

export async function uploadFile(
  file: File,
  datasetContext: DatasetContext
) {
  const form = new FormData()
  form.append('file', file)
  form.append('dataset_context', datasetContext)
  return coldStartRequest<any>({
    url: '/api/upload',
    method: 'POST',
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function uploadDemoDataset(
  demoDataset: string,
  datasetContext: DatasetContext
) {
  const form = new FormData()
  form.append('demo_dataset', demoDataset)
  form.append('dataset_context', datasetContext)
  return coldStartRequest<any>({
    url: '/api/upload',
    method: 'POST',
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function getProfile(sessionId: string) {
  return coldStartRequest<any>({ url: `/api/profile/${sessionId}`, method: 'GET' })
}

export async function getSessionData(sessionId: string, limit: number = 500) {
  return coldStartRequest<{
    session_id: string
    rows: Record<string, unknown>[]
    total_rows: number
    returned_rows: number
    columns: string[]
  }>({ url: `/api/data/${sessionId}`, method: 'GET', params: { limit } })
}

export interface RestoredSession {
  session_id: string
  found: boolean
  filename: string
  dataset_context: string
  cleaning_log: string[]
  rows_before: number
  rows_after: number
  preview_rows: Record<string, unknown>[]
  profile_data: any | null
  summary_data: any | null
  score_data: any | null
  whatif_data: any | null
  time_to_insight_ms: number | null
  rapids_active: boolean
  avg_nulls_pct: number
  created_at: string | null
}

export async function restoreSession(sessionId: string): Promise<RestoredSession> {
  return coldStartRequest<RestoredSession>({ url: `/api/restore/${sessionId}`, method: 'GET' })
}

export interface LlmTierInfo {
  name: string
  type: 'cloud' | 'local' | 'static'
  active: boolean
}

export interface LlmStatus {
  model: string
  rpm_limit: number
  calls_last_minute: number
  cache_entries: number
  api_key_configured: boolean
  last_tier_used: {
    tier: string         // "gemini" / "nvidia_nim" / "ollama" / "mock" / "none"
    tier_rank: number    // 0-4
    label: string
    color: string
    icon: string
  }
  circuit_breaker: {
    active: boolean
    remaining_sec: number
    reason?: string
  }
  tiers: LlmTierInfo[]
}

export async function getLlmStatus(): Promise<LlmStatus> {
  // Short-circuit: don't go through coldStartRequest because we want a
  // FAST timeout here (5s) — this endpoint is polled every 5s by the badge.
  try {
    const res = await api.get<LlmStatus>('/api/llm-status', { timeout: 5000 })
    return res.data
  } catch {
    throw new Error('LLM status unavailable')
  }
}

export async function getSummary(sessionId: string) {
  return coldStartRequest<any>({ url: `/api/summary/${sessionId}`, method: 'POST' })
}

export async function getDecisionScore(sessionId: string) {
  return coldStartRequest<any>({ url: `/api/decision-score/${sessionId}`, method: 'POST' })
}

export async function runWhatIf(
  sessionId: string,
  column: string,
  pctChange: number
) {
  return coldStartRequest<any>({
    url: `/api/whatif/${sessionId}`,
    method: 'POST',
    data: { column, pct_change: pctChange },
  })
}

export async function generateReport(sessionId: string): Promise<Blob> {
  // Blob responses need special handling — don't go through coldStartRequest
  // because it expects parsed JSON. Use api directly with cold-start timeout.
  const res = await api.post(`/api/report/${sessionId}`, null, {
    responseType: 'blob',
    timeout: _warmth === 'warm' ? WARM_TIMEOUT : COLD_START_TIMEOUT,
  })
  return res.data
}

export async function sendChat(
  sessionId: string,
  message: string,
  history: { role: string; content: string }[]
) {
  return coldStartRequest<any>({
    url: `/api/chat/${sessionId}`,
    method: 'POST',
    data: { message, history },
  })
}

export async function getForecast(
  sessionId: string,
  column: string,
  periods: number = 3
) {
  return coldStartRequest<any>({
    url: `/api/forecast/${sessionId}`,
    method: 'GET',
    params: { column, periods },
  })
}

export async function runAutomation(
  sessionId: string,
  recommendationText: string
) {
  return coldStartRequest<any>({
    url: `/api/automate/${sessionId}`,
    method: 'POST',
    data: { recommendation_text: recommendationText },
  })
}
