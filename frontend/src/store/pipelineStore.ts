import { create } from 'zustand'

export type PipelineStep =
  | 'idle'
  | 'uploading'
  | 'cleaning'
  | 'profiling'
  | 'summarizing'
  | 'scoring'
  | 'done'

export type RiskLevel = 'Low' | 'Medium' | 'High'
export type DatasetContext = 'business' | 'personal_finance' | 'student' | 'civic'

export interface ColumnProfile {
  name: string
  dtype: string
  nulls_pct: number
  unique_count: number
  min?: number
  max?: number
  mean?: number
  std?: number
  outlier_count: number
  sample_values: unknown[]
}

export interface ProfileData {
  session_id: string
  row_count: number
  column_count: number
  columns: ColumnProfile[]
  correlations: Record<string, Record<string, number>>
  overall_quality_pct: number
  numeric_cols: string[]
}

export interface SubScores {
  data_quality: number
  trend_stability: number
  risk_inverse: number
  opportunity: number
}

export interface Priority {
  text: string
  rationale: string
  impact_tag: string
}

export interface Recommendation {
  action: string
  rationale: string
  priority: string
}

export interface ScoreData {
  session_id: string
  score: number
  risk_level: RiskLevel
  confidence: number
  sub_scores: SubScores
  top_priorities: Priority[]
  recommendations: Recommendation[]
  time_to_insight_ms: number
}

export interface WhatIfResult {
  session_id: string
  column: string
  pct_change: number
  old_score: { score: number; risk_level: RiskLevel; confidence: number; sub_scores: SubScores }
  new_score: { score: number; risk_level: RiskLevel; confidence: number; sub_scores: SubScores }
  delta_explanation: string
}

export interface SummaryData {
  session_id: string
  summary_text: string
  key_findings: string[]
}

interface PipelineStore {
  // Session
  sessionId: string | null
  filename: string
  datasetContext: DatasetContext

  // Pipeline state
  step: PipelineStep
  currentStatusLabel: string
  startTimeMs: number | null

  // Data
  cleaningLog: string[]
  rowsBefore: number
  rowsAfter: number
  previewRows: Record<string, unknown>[]
  profileData: ProfileData | null
  summaryData: SummaryData | null
  scoreData: ScoreData | null
  whatIfResult: WhatIfResult | null
  rapidsActive: boolean

  // Error
  error: string | null

  // Actions
  setStep: (step: PipelineStep, label?: string) => void
  setSessionId: (id: string) => void
  setFilename: (name: string) => void
  setDatasetContext: (ctx: DatasetContext) => void
  setCleaningLog: (log: string[], rowsBefore: number, rowsAfter: number) => void
  setPreviewRows: (rows: Record<string, unknown>[]) => void
  setProfileData: (data: ProfileData) => void
  setSummaryData: (data: SummaryData) => void
  setScoreData: (data: ScoreData) => void
  setWhatIfResult: (result: WhatIfResult | null) => void
  setRapidsActive: (active: boolean) => void
  setError: (err: string | null) => void
  startClock: () => void
  reset: () => void
}

export const usePipelineStore = create<PipelineStore>((set) => ({
  sessionId: null,
  filename: '',
  datasetContext: 'business',
  step: 'idle',
  currentStatusLabel: '',
  startTimeMs: null,
  cleaningLog: [],
  rowsBefore: 0,
  rowsAfter: 0,
  previewRows: [],
  profileData: null,
  summaryData: null,
  scoreData: null,
  whatIfResult: null,
  rapidsActive: false,
  error: null,

  setStep: (step, label = '') => set({ step, currentStatusLabel: label }),
  setSessionId: (id) => set({ sessionId: id }),
  setFilename: (name) => set({ filename: name }),
  setDatasetContext: (ctx) => set({ datasetContext: ctx }),
  setCleaningLog: (log, rowsBefore, rowsAfter) => set({ cleaningLog: log, rowsBefore, rowsAfter }),
  setPreviewRows: (rows) => set({ previewRows: rows }),
  setProfileData: (data) => set({ profileData: data }),
  setSummaryData: (data) => set({ summaryData: data }),
  setScoreData: (data) => set({ scoreData: data }),
  setWhatIfResult: (result) => set({ whatIfResult: result }),
  setRapidsActive: (active) => set({ rapidsActive: active }),
  setError: (err) => set({ error: err }),
  startClock: () => set({ startTimeMs: Date.now() }),
  reset: () => set({
    sessionId: null, filename: '', step: 'idle', currentStatusLabel: '',
    startTimeMs: null, cleaningLog: [], rowsBefore: 0, rowsAfter: 0,
    previewRows: [], profileData: null, summaryData: null, scoreData: null,
    whatIfResult: null, rapidsActive: false, error: null
  }),
}))
