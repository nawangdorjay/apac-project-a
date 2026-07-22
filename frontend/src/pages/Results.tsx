import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import { usePipelineStore } from '../store/pipelineStore'
import { generateReport } from '../lib/api'
import type { ColumnProfile } from '../store/pipelineStore'

// Score Gauge SVG component
function ScoreGauge({ score, riskLevel }: { score: number; riskLevel: string }) {
  const [displayed, setDisplayed] = useState(0)
  const radius = 80
  const circumference = 2 * Math.PI * radius
  const halfCirc = circumference / 2  // semicircle
  const offset = halfCirc - (score / 100) * halfCirc

  useEffect(() => {
    const timer = setTimeout(() => setDisplayed(score), 100)
    return () => clearTimeout(timer)
  }, [score])

  const riskColor = riskLevel === 'Low' ? '#16A34A' : riskLevel === 'Medium' ? '#D97706' : '#DC2626'

  return (
    <div style={{ position: 'relative', textAlign: 'center' }}>
      <svg width="200" height="110" viewBox="0 0 200 110">
        {/* Background track */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none" stroke="#E2E8F0" strokeWidth="14"
          strokeLinecap="round"
        />
        {/* Score arc */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none" stroke={riskColor} strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={halfCirc}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)' }}
        />
        {/* Score text */}
        <text x="100" y="88" textAnchor="middle" fontSize="36" fontWeight="800" fill="#1E293B" fontFamily="Space Grotesk, sans-serif">
          {Math.round(displayed)}
        </text>
        <text x="100" y="108" textAnchor="middle" fontSize="11" fill="#94A3B8" fontFamily="Inter, sans-serif">
          out of 100
        </text>
      </svg>
    </div>
  )
}

function AutoChart({ col, data }: { col: ColumnProfile; data: Record<string, unknown>[] }) {
  const isNumeric = col.dtype.includes('int') || col.dtype.includes('float')
  if (!isNumeric || data.length === 0) return null

  // Find the best X-axis key dynamically
  let xKey = Object.keys(data[0] || {})[0] || ''
  const timeKeys = ['month', 'date', 'year', 'quarter', 'time', 'timestamp', 'period', 'week', 'day']
  const foundTimeKey = Object.keys(data[0] || {}).find(k => 
    timeKeys.some(tk => k.toLowerCase().includes(tk))
  )
  if (foundTimeKey) {
    xKey = foundTimeKey
  } else {
    // Look for the first column that has multiple unique values (is not constant)
    const keys = Object.keys(data[0] || {})
    for (const key of keys) {
      if (key === col.name) continue
      const uniqueValues = new Set(data.map(row => String(row[key] ?? '')))
      if (uniqueValues.size > 1) {
        xKey = key
        break
      }
    }
  }
  
  // Aggregate values by selected X-axis key
  const grouped: Record<string, { sum: number; count: number }> = {}
  data.forEach(row => {
    const name = String(row[xKey] ?? '')
    const val = Number(row[col.name])
    if (!isNaN(val)) {
      if (!grouped[name]) {
        grouped[name] = { sum: 0, count: 0 }
      }
      grouped[name].sum += val
      grouped[name].count += 1
    }
  })

  const values = Object.keys(grouped).map(name => ({
    name,
    value: Number((grouped[name].sum / grouped[name].count).toFixed(2))
  }))

  if (values.length === 0) return null

  const COLORS = ['#2563EB', '#7C3AED', '#16A34A', '#D97706', '#DC2626', '#0891B2']

  if (values.length <= 12) {
    return (
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={values} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94A3B8' }} />
          <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E2E8F0' }} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {values.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={values} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94A3B8' }} />
        <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E2E8F0' }} />
        <Line type="monotone" dataKey="value" stroke="#2563EB" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default function Results() {
  const navigate = useNavigate()
  const store = usePipelineStore()
  const [showBreakdown, setShowBreakdown] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])

  // New forecasting & automation state
  const [selectedForecastCol, setSelectedForecastCol] = useState<string>('')
  const [forecastData, setForecastData] = useState<any>(null)
  const [forecastLoading, setForecastLoading] = useState(false)
  const [forecastMessage, setForecastMessage] = useState('')
  const [automationResult, setAutomationResult] = useState<any>(null)
  const [automationLoading, setAutomationLoading] = useState(false)
  const [activeRecommendation, setActiveRecommendation] = useState<string>('')

  const { scoreData, profileData, summaryData, sessionId } = store

  // Fetch forecast data helper
  const handleFetchForecast = async (col: string) => {
    if (!sessionId || !col) return
    setForecastLoading(true)
    try {
      const { getForecast } = await import('../lib/api')
      const data = await getForecast(sessionId, col)
      setForecastData(data)
      setForecastMessage(data.message)
    } catch (e) {
      console.error('Forecast failed', e)
    } finally {
      setForecastLoading(false)
    }
  }

  // Trigger automation helper
  const handleTriggerAutomation = async (recText: string) => {
    if (!sessionId || automationLoading) return
    setAutomationLoading(true)
    setActiveRecommendation(recText)
    try {
      const { runAutomation } = await import('../lib/api')
      const data = await runAutomation(sessionId, recText)
      setAutomationResult(data)
    } catch (e) {
      console.error('Automation failed', e)
    } finally {
      setAutomationLoading(false)
    }
  }

  useEffect(() => {
    if (!sessionId || !scoreData) {
      navigate('/')
      return
    }
    const numericCols = profileData?.columns.filter(c => c.dtype.includes('int') || c.dtype.includes('float')) ?? []
    if (numericCols.length > 0) {
      const firstCol = numericCols[0].name
      setSelectedForecastCol(firstCol)
      handleFetchForecast(firstCol)
    }
  }, [])

  if (!scoreData || !profileData) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⚡</div>
          <p style={{ color: '#64748B' }}>No results yet. <Link to="/">Start fresh</Link></p>
        </div>
      </div>
    )
  }

  const timeToInsightSec = scoreData.time_to_insight_ms ? (scoreData.time_to_insight_ms / 1000).toFixed(1) : null
  const riskColor = scoreData.risk_level === 'Low' ? '#16A34A' : scoreData.risk_level === 'Medium' ? '#D97706' : '#DC2626'
  const riskBadgeClass = `badge badge-${scoreData.risk_level.toLowerCase()}`

  const handleExport = async () => {
    if (!sessionId || exporting) return
    setExporting(true)
    try {
      const blob = await generateReport(sessionId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'DecisionLens_Report.pdf'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Export failed', e)
    } finally {
      setExporting(false)
    }
  }

  const numericCols = profileData.columns.filter(c => c.dtype.includes('int') || c.dtype.includes('float'))

  const forecastChartData: any[] = []
  if (forecastData) {
    forecastData.historical.forEach((pt: any) => {
      forecastChartData.push({
        name: `M${pt.index + 1}`,
        Historical: pt.value,
        Projected: null,
      })
    })
    if (forecastData.historical.length > 0) {
      const lastHist = forecastData.historical[forecastData.historical.length - 1]
      forecastChartData.push({
        name: `M${lastHist.index + 1}`,
        Historical: lastHist.value,
        Projected: lastHist.value,
      })
    }
    forecastData.projected.forEach((pt: any) => {
      forecastChartData.push({
        name: `M${pt.index + 1} (Proj)`,
        Historical: null,
        Projected: pt.value,
      })
    })
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F8FAFC' }}>
      {/* Nav */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', height: 60, background: 'white', borderBottom: '1px solid #E2E8F0',
        position: 'sticky', top: 0, zIndex: 100
      }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
          <div style={{ width: 26, height: 26, background: '#2563EB', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          <span style={{ fontFamily: 'Space Grotesk, sans-serif', fontWeight: 700, fontSize: 15, color: '#1E293B' }}>DecisionLens AI</span>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 13, color: '#64748B' }}>{store.filename}</span>
          <button className="btn-secondary" style={{ fontSize: 12, padding: '6px 12px' }} onClick={() => setChatOpen(!chatOpen)}>
            💬 Chat with Data
          </button>
          <button className="btn-primary" style={{ fontSize: 12, padding: '6px 12px' }} onClick={handleExport} disabled={exporting}>
            {exporting ? '⏳ Generating...' : '📄 Export PDF'}
          </button>
          <Link to="/" className="btn-ghost" onClick={() => store.reset()}>New Analysis</Link>
        </div>
      </nav>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>

        {/* Time to Insight banner */}
        {timeToInsightSec && (
          <div className="animate-fade-in-up" style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 10,
            padding: '12px 20px', marginBottom: 20
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 20 }}>⚡</span>
              <div>
                <span style={{ fontSize: 15, fontWeight: 700, color: '#1D4ED8' }}>Time to Insight: {timeToInsightSec}s</span>
                <span style={{ fontSize: 13, color: '#64748B', marginLeft: 12 }}>Manual analysis typically takes 15–30 minutes</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {store.rapidsActive && (
                <span style={{ fontSize: 12, padding: '3px 10px', background: '#DCFCE7', borderRadius: 20, color: '#16A34A', fontWeight: 600, border: '1px solid #BBF7D0' }}>
                  ⚡ NVIDIA RAPIDS GPU
                </span>
              )}
              <span style={{ fontSize: 12, padding: '3px 10px', background: '#DBEAFE', borderRadius: 20, color: '#1D4ED8', fontWeight: 500 }}>
                Gemini 2.0 Flash
              </span>
              <span style={{ fontSize: 12, padding: '3px 10px', background: '#DBEAFE', borderRadius: 20, color: '#1D4ED8', fontWeight: 500 }}>
                Cloud Run
              </span>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, marginBottom: 20 }}>

          {/* Decision Score Card */}
          <div className="card animate-fade-in-up" style={{ gridColumn: '1', textAlign: 'center' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B', marginBottom: 12, textAlign: 'left' }}>DECISION SCORE</div>
            <ScoreGauge score={scoreData.score} riskLevel={scoreData.risk_level} />
            <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 12 }}>
              <span className={riskBadgeClass}>{scoreData.risk_level} Risk</span>
              <span className="badge" style={{ background: '#F0FDF4', color: '#16A34A' }}>
                {scoreData.confidence.toFixed(0)}% Confidence
              </span>
            </div>

            {/* Breakdown toggle */}
            <button
              className="btn-ghost"
              style={{ marginTop: 16, width: '100%', justifyContent: 'center', color: '#2563EB', fontSize: 12, fontWeight: 600 }}
              onClick={() => setShowBreakdown(!showBreakdown)}
            >
              {showBreakdown ? '▲ Hide Breakdown' : '▼ View Score Breakdown'}
            </button>

            {showBreakdown && (
              <div className="animate-fade-in-up" style={{ marginTop: 16, textAlign: 'left' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', marginBottom: 10 }}>
                  FORMULA: 0.35 × Quality + 0.25 × Stability + 0.25 × Risk⁻¹ + 0.15 × Opportunity
                </div>
                {[
                  { label: 'Data Quality', weight: '35%', value: scoreData.sub_scores.data_quality, note: 'Completeness, types, outliers' },
                  { label: 'Trend Stability', weight: '25%', value: scoreData.sub_scores.trend_stability, note: 'Coefficient of variation' },
                  { label: 'Risk Inverse', weight: '25%', value: scoreData.sub_scores.risk_inverse, note: 'Anomaly density inverted' },
                  { label: 'Opportunity (AI)', weight: '15%', value: scoreData.sub_scores.opportunity, note: 'Gemini-assessed potential' },
                ].map(sub => (
                  <div key={sub.label} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <div>
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1E293B' }}>{sub.label}</span>
                        <span style={{ fontSize: 11, color: '#94A3B8', marginLeft: 6 }}>({sub.weight})</span>
                      </div>
                      <span style={{ fontSize: 13, fontWeight: 700, color: '#1E293B' }}>{sub.value.toFixed(1)}</span>
                    </div>
                    <div style={{ height: 6, background: '#F1F5F9', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: 3, background: sub.value >= 70 ? '#16A34A' : sub.value >= 50 ? '#D97706' : '#DC2626',
                        width: `${sub.value}%`, transition: 'width 1s ease'
                      }} />
                    </div>
                    <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 2 }}>{sub.note}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Summary */}
          <div className="card animate-fade-in-up" style={{ gridColumn: '2 / 4' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B', marginBottom: 12 }}>AI SUMMARY</div>
            {summaryData && (
              <>
                <p style={{ fontSize: 14, color: '#1E293B', lineHeight: 1.7, marginBottom: 16 }}>
                  {summaryData.summary_text}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {summaryData.key_findings.map((f, i) => (
                    <div key={i} style={{
                      display: 'flex', gap: 8, padding: '8px 12px',
                      background: '#F8FAFC', borderRadius: 8, fontSize: 13, color: '#475569'
                    }}>
                      <span style={{ color: '#2563EB', fontWeight: 700, flexShrink: 0 }}>→</span>
                      {f}
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Profile stats */}
            <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
              {[
                { label: 'Rows', value: profileData.row_count.toLocaleString() },
                { label: 'Columns', value: profileData.column_count },
                { label: 'Quality', value: `${profileData.overall_quality_pct.toFixed(1)}%` },
                { label: 'Nulls', value: `${(profileData.columns.reduce((a, c) => a + c.nulls_pct, 0) / profileData.columns.length).toFixed(1)}%` },
              ].map(stat => (
                <div key={stat.label} style={{
                  flex: 1, textAlign: 'center', padding: '10px 8px',
                  background: '#F8FAFC', borderRadius: 8, border: '1px solid #E2E8F0'
                }}>
                  <div style={{ fontSize: 18, fontWeight: 800, color: '#1E293B', fontFamily: 'Space Grotesk, sans-serif' }}>{stat.value}</div>
                  <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Priorities */}
        <div className="card animate-fade-in-up" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B', marginBottom: 16 }}>TOP 3 PRIORITIES</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {scoreData.top_priorities.slice(0, 3).map((p, i) => {
              const impactClass = p.impact_tag?.includes('High') ? 'tag-high' : p.impact_tag?.includes('Medium') ? 'tag-medium' : 'tag-quick'
              return (
                <div key={i} style={{ padding: 16, background: '#F8FAFC', borderRadius: 10, border: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <span style={{
                      width: 24, height: 24, borderRadius: '50%', background: '#EFF6FF',
                      border: '1px solid #BFDBFE', display: 'flex', alignItems: 'center',
                      justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#2563EB', flexShrink: 0
                    }}>{i + 1}</span>
                    <span className={`badge ${impactClass}`} style={{ fontSize: 10 }}>{p.impact_tag}</span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#1E293B', marginBottom: 6 }}>{p.text}</div>
                  <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.5 }}>{p.rationale}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Charts */}
        {numericCols.length > 0 && (
          <div className="card animate-fade-in-up" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B' }}>DASHBOARD</div>
              <span style={{ fontSize: 12, color: '#94A3B8' }}>
                Auto-selected chart type per column · {store.chartRows.length > 0 ? `${store.chartRows.length} rows` : '5 preview rows'} shown
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
              {numericCols.slice(0, 6).map(col => (
                <div key={col.name} style={{ background: '#F8FAFC', borderRadius: 10, padding: '14px' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#64748B', marginBottom: 8 }}>
                    {col.name}
                    {col.outlier_count > 0 && (
                      <span style={{ marginLeft: 8, fontSize: 10, color: '#D97706', background: '#FEF3C7', padding: '1px 6px', borderRadius: 10 }}>
                        {col.outlier_count} outliers
                      </span>
                    )}
                  </div>
                  <AutoChart col={col} data={store.chartRows.length > 0 ? store.chartRows : store.previewRows} />
                  <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                    {col.mean !== undefined && <span style={{ fontSize: 11, color: '#94A3B8' }}>Mean: {col.mean?.toFixed(1)}</span>}
                    {col.std !== undefined && <span style={{ fontSize: 11, color: '#94A3B8' }}>Std: {col.std?.toFixed(1)}</span>}
                    <span style={{ fontSize: 11, color: '#94A3B8' }}>Nulls: {col.nulls_pct.toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Outcome Prediction (Forecasting) */}
        {numericCols.length > 0 && (
          <div className="card animate-fade-in-up" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B' }}>🔮 OUTCOME PREDICTION & FORECASTING</div>
                <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>GPU-accelerated linear trend projections (next 3 periods)</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, color: '#475569', fontWeight: 500 }}>Select Variable:</span>
                <select
                  value={selectedForecastCol}
                  onChange={(e) => {
                    setSelectedForecastCol(e.target.value)
                    handleFetchForecast(e.target.value)
                  }}
                  style={{
                    padding: '6px 12px', border: '1px solid #E2E8F0', borderRadius: 8,
                    fontSize: 12, color: '#1E293B', outline: 'none', background: 'white'
                  }}
                >
                  {numericCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                </select>
              </div>
            </div>

            {forecastLoading ? (
              <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div className="status-chip">
                  <div className="dot"></div>
                  Generating projections...
                </div>
              </div>
            ) : (
              <div>
                {forecastChartData.length > 0 && (
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={forecastChartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94A3B8' }} />
                      <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} />
                      <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E2E8F0' }} />
                      <Line type="monotone" dataKey="Historical" stroke="#2563EB" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                      <Line type="monotone" dataKey="Projected" stroke="#7C3AED" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
                {forecastMessage && (
                  <div style={{ marginTop: 12, display: 'flex', gap: 8, padding: '10px 14px', background: '#F8FAFC', borderRadius: 8, border: '1px solid #E2E8F0' }}>
                    <span style={{ fontSize: 16 }}>📈</span>
                    <span style={{ fontSize: 13, color: '#475569', lineHeight: 1.5 }}>
                      {forecastMessage}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Recommendations */}
        {scoreData.recommendations?.length > 0 && (
          <div className="card animate-fade-in-up" style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B', marginBottom: 16 }}>RECOMMENDED ACTIONS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {scoreData.recommendations.map((r, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                  padding: '12px 16px', background: '#F8FAFC', borderRadius: 8, border: '1px solid #E2E8F0', flexWrap: 'wrap'
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, minWidth: 260, flex: 1 }}>
                    <div style={{
                      padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 700, flexShrink: 0, marginTop: 2,
                      background: r.priority === 'High' ? '#FEE2E2' : r.priority === 'Medium' ? '#FEF3C7' : '#F0FDF4',
                      color: r.priority === 'High' ? '#DC2626' : r.priority === 'Medium' ? '#D97706' : '#16A34A'
                    }}>{r.priority}</div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#1E293B', marginBottom: 2 }}>{r.action}</div>
                      <div style={{ fontSize: 12, color: '#64748B' }}>{r.rationale}</div>
                    </div>
                  </div>
                  <button 
                    className="btn-primary" 
                    style={{ fontSize: 11, padding: '6px 12px', background: '#7C3AED', flexShrink: 0 }}
                    onClick={() => handleTriggerAutomation(r.action)}
                    disabled={automationLoading && activeRecommendation === r.action}
                  >
                    {automationLoading && activeRecommendation === r.action ? '⏳ Triggering...' : '⚡ Automate Workflow'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What-If CTA */}
        <div style={{
          background: 'linear-gradient(135deg, #1E293B 0%, #1D4ED8 100%)',
          borderRadius: 12, padding: '28px 32px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16
        }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'white', marginBottom: 6 }}>
              🔮 What if you changed something?
            </div>
            <div style={{ fontSize: 14, color: '#94A3B8' }}>
              Run a scenario simulation — see how your Decision Score changes before you act
            </div>
          </div>
          <Link to="/whatif" className="btn-primary" style={{ background: 'white', color: '#1D4ED8' }}>
            Open What-If Simulator →
          </Link>
        </div>
      </div>

      {/* Simple chat panel */}
      {chatOpen && (
        <div style={{
          position: 'fixed', right: 24, bottom: 24, width: 360,
          background: 'white', borderRadius: 12, border: '1px solid #E2E8F0',
          boxShadow: '0 20px 60px rgba(0,0,0,0.15)', zIndex: 200
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '14px 16px', borderBottom: '1px solid #E2E8F0'
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#1E293B' }}>💬 Chat with Your Data</div>
            <button className="btn-ghost" style={{ padding: '4px 8px' }} onClick={() => setChatOpen(false)}>✕</button>
          </div>
          <div style={{ height: 260, overflow: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {chatHistory.length === 0 && (
              <div style={{ color: '#94A3B8', fontSize: 13, textAlign: 'center', marginTop: 60 }}>
                Ask anything about your dataset...
                <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {['What are the top trends?', 'Which column has most outliers?', 'What drives the score?'].map(q => (
                    <button key={q} className="btn-secondary" style={{ fontSize: 11, padding: '6px 10px' }}
                      onClick={() => setChatInput(q)}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {chatHistory.map((msg, i) => (
              <div key={i} style={{
                padding: '8px 12px', borderRadius: 8, maxWidth: '85%', fontSize: 13,
                background: msg.role === 'user' ? '#EFF6FF' : '#F8FAFC',
                color: msg.role === 'user' ? '#1D4ED8' : '#1E293B',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                border: `1px solid ${msg.role === 'user' ? '#BFDBFE' : '#E2E8F0'}`
              }}>
                {msg.content}
              </div>
            ))}
          </div>
          <div style={{ padding: '12px 16px', borderTop: '1px solid #E2E8F0', display: 'flex', gap: 8 }}>
            <input
              type="text"
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={async e => {
                if (e.key === 'Enter' && chatInput.trim() && sessionId) {
                  const msg = chatInput.trim()
                  setChatInput('')
                  const newHistory = [...chatHistory, { role: 'user', content: msg }]
                  setChatHistory(newHistory)
                  try {
                    const { sendChat } = await import('../lib/api')
                    const res = await sendChat(sessionId, msg, newHistory)
                    setChatHistory([...newHistory, { role: 'assistant', content: res.reply }])
                  } catch {
                    setChatHistory([...newHistory, { role: 'assistant', content: 'Sorry, chat is unavailable right now.' }])
                  }
                }
              }}
              placeholder="Ask about your data..."
              style={{
                flex: 1, padding: '8px 12px', border: '1px solid #E2E8F0',
                borderRadius: 8, fontSize: 13, outline: 'none', color: '#1E293B'
              }}
            />
          </div>
        </div>
      )}

      {/* Automation Modal Overlay */}
      {automationResult && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }} className="animate-fade-in-up">
          <div className="card" style={{ maxWidth: 480, width: '90%', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 24 }}>⚙️</span>
                <span style={{ fontSize: 16, fontWeight: 700, color: '#1E293B' }}>Intelligent Automation Flow</span>
              </div>
              <button className="btn-ghost" style={{ padding: '4px 8px' }} onClick={() => setAutomationResult(null)}>✕</button>
            </div>
            
            <div style={{ background: '#F8FAFC', borderRadius: 8, padding: 16, border: '1px solid #E2E8F0', marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#64748B' }}>STATUS</span>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                  background: automationResult.status === 'Completed' ? '#DCFCE7' : '#EFF6FF',
                  color: automationResult.status === 'Completed' ? '#16A34A' : '#1D4ED8'
                }}>
                  {automationResult.status}
                </span>
              </div>
              <div style={{ fontSize: 14, color: '#1E293B', fontWeight: 600, marginBottom: 12 }}>
                {automationResult.message}
              </div>
              <div style={{ fontSize: 11, color: '#94A3B8' }}>
                Triggered at: {new Date(automationResult.timestamp).toLocaleTimeString()}
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', marginBottom: 8 }}>WORKFLOW INTEGRATION DETAILS</div>
              <div style={{ fontSize: 13, color: '#475569', marginBottom: 4 }}>
                <strong>Workflow Type:</strong> {automationResult.details.workflow_type}
              </div>
              <div style={{ fontSize: 13, color: '#475569', marginBottom: 4 }}>
                <strong>Trigger Action:</strong> {automationResult.details.action_taken}
              </div>
              <div style={{ fontSize: 13, color: '#475569' }}>
                <strong>Google Cloud Service:</strong> <span style={{ color: '#2563EB', fontWeight: 600 }}>{automationResult.details.integration}</span>
              </div>
            </div>

            <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => setAutomationResult(null)}>
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
