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
