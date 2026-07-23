import axios from 'axios'
import { DatasetContext } from '../store/pipelineStore'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
})

export async function uploadFile(
  file: File,
  datasetContext: DatasetContext
) {
  const form = new FormData()
  form.append('file', file)
  form.append('dataset_context', datasetContext)
  const res = await api.post('/api/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function uploadDemoDataset(
  demoDataset: string,
  datasetContext: DatasetContext
) {
  const form = new FormData()
  form.append('demo_dataset', demoDataset)
  form.append('dataset_context', datasetContext)
  const res = await api.post('/api/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function getProfile(sessionId: string) {
  const res = await api.get(`/api/profile/${sessionId}`)
  return res.data
}

export async function getSessionData(sessionId: string, limit: number = 500) {
  const res = await api.get(`/api/data/${sessionId}`, { params: { limit } })
  return res.data as {
    session_id: string
    rows: Record<string, unknown>[]
    total_rows: number
    returned_rows: number
    columns: string[]
  }
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
  const res = await api.get(`/api/restore/${sessionId}`)
  return res.data
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
  const res = await api.get('/api/llm-status')
  return res.data
}

export async function getSummary(sessionId: string) {
  const res = await api.post(`/api/summary/${sessionId}`)
  return res.data
}

export async function getDecisionScore(sessionId: string) {
  const res = await api.post(`/api/decision-score/${sessionId}`)
  return res.data
}

export async function runWhatIf(
  sessionId: string,
  column: string,
  pctChange: number
) {
  const res = await api.post(`/api/whatif/${sessionId}`, {
    column,
    pct_change: pctChange,
  })
  return res.data
}

export async function generateReport(sessionId: string): Promise<Blob> {
  const res = await api.post(`/api/report/${sessionId}`, null, {
    responseType: 'blob',
  })
  return res.data
}

export async function sendChat(
  sessionId: string,
  message: string,
  history: { role: string; content: string }[]
) {
  const res = await api.post(`/api/chat/${sessionId}`, { message, history })
  return res.data
}

export async function getForecast(
  sessionId: string,
  column: string,
  periods: number = 3
) {
  const res = await api.get(`/api/forecast/${sessionId}`, {
    params: { column, periods }
  })
  return res.data
}

export async function runAutomation(
  sessionId: string,
  recommendationText: string
) {
  const res = await api.post(`/api/automate/${sessionId}`, {
    recommendation_text: recommendationText
  })
  return res.data
}
