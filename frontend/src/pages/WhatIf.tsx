import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { usePipelineStore } from '../store/pipelineStore'
import { runWhatIf, generateReport } from '../lib/api'

export default function WhatIf() {
  const navigate = useNavigate()
  const store = usePipelineStore()

  const { sessionId, scoreData, profileData, whatIfResult } = store

  const [selectedCol, setSelectedCol] = useState<string>('')
  const [pctChange, setPctChange] = useState<number>(0)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId || !scoreData) {
      navigate('/')
      return
    }
    const numericCols = profileData?.numeric_cols ?? []
    if (numericCols.length > 0 && !selectedCol) {
      setSelectedCol(numericCols[0])
    }
  }, [])

  if (!scoreData || !profileData) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: '#64748B' }}>No data. <Link to="/">Start fresh →</Link></p>
      </div>
    )
  }

  const numericCols = profileData.numeric_cols ?? []
  const riskColor = (level: string) => level === 'Low' ? '#16A34A' : level === 'Medium' ? '#D97706' : '#DC2626'

  const handleRun = async () => {
    if (!sessionId || !selectedCol || loading) return
    setLoading(true)
    setError(null)
    try {
      const result = await runWhatIf(sessionId, selectedCol, pctChange)
      store.setWhatIfResult(result)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

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
    } catch {
      setError('PDF export failed')
    } finally {
      setExporting(false)
    }
  }

  const scoreChange = whatIfResult
    ? whatIfResult.new_score.score - whatIfResult.old_score.score
    : null

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
        <div style={{ display: 'flex', gap: 10 }}>
          <Link to="/results" className="btn-ghost">← Back to Results</Link>
          <button className="btn-primary" style={{ fontSize: 12, padding: '6px 12px' }} onClick={handleExport} disabled={exporting}>
            {exporting ? '⏳ Generating...' : '📄 Export PDF (with this scenario)'}
          </button>
        </div>
      </nav>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 24px' }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '4px 12px', background: '#FEF3C7', border: '1px solid #FDE68A',
            borderRadius: 20, marginBottom: 12
          }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#D97706' }}>
              ⚠ TREND PROJECTION — SCENARIO SIMULATION ONLY · NOT A FORECAST
            </span>
          </div>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#1E293B', marginBottom: 8 }}>
            🔮 What-If Simulator
          </h1>
          <p style={{ color: '#64748B', fontSize: 15 }}>
            Adjust a column value and see how your Decision Score changes — before you act on it.
            This uses the <strong>same deterministic scoring formula</strong>, not a black-box prediction.
          </p>
        </div>

        {/* Simulator Controls */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B', marginBottom: 16 }}>CONFIGURE SCENARIO</div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
            {/* Column picker */}
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, color: '#1E293B', display: 'block', marginBottom: 8 }}>
                Select Column to Adjust
              </label>
              <select
                value={selectedCol}
                onChange={e => setSelectedCol(e.target.value)}
                style={{
                  width: '100%', padding: '10px 12px', border: '1px solid #E2E8F0',
                  borderRadius: 8, fontSize: 13, color: '#1E293B', background: 'white',
                  outline: 'none', cursor: 'pointer'
                }}
              >
                {numericCols.map(col => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>

            {/* Percentage change */}
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, color: '#1E293B', display: 'block', marginBottom: 8 }}>
                Change by: <span style={{ color: '#2563EB' }}>{pctChange > 0 ? '+' : ''}{pctChange}%</span>
              </label>
              <input
                type="range"
                min={-50}
                max={50}
                value={pctChange}
                onChange={e => setPctChange(Number(e.target.value))}
                style={{ marginBottom: 8 }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94A3B8' }}>
                <span>−50%</span>
                <span>0%</span>
                <span>+50%</span>
              </div>
            </div>
          </div>

          {/* Quick scenario buttons */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: '#64748B', alignSelf: 'center' }}>Quick scenarios:</span>
            {[-20, -10, +10, +20].map(pct => (
              <button key={pct} className="btn-secondary" style={{ fontSize: 12, padding: '5px 12px' }}
                onClick={() => setPctChange(pct)}>
                {pct > 0 ? '+' : ''}{pct}%
              </button>
            ))}
          </div>

          {/* Scenario description */}
          {selectedCol && (
            <div style={{
              padding: '12px 16px', background: '#F8FAFC', borderRadius: 8,
              border: '1px solid #E2E8F0', marginBottom: 20, fontSize: 14, color: '#475569'
            }}>
              📊 Simulating: <strong>"{selectedCol}"</strong> adjusted by <strong>{pctChange > 0 ? '+' : ''}{pctChange}%</strong>
              {pctChange === 0 && ' — move the slider to define a scenario'}
            </div>
          )}

          <button
            className="btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', fontSize: 15 }}
            onClick={handleRun}
            disabled={loading || !selectedCol || pctChange === 0}
          >
            {loading ? (
              <>
                <div className="dot" style={{ background: 'white' }}></div>
                Running scenario simulation...
              </>
            ) : (
              '🔮 Run Scenario Simulation'
            )}
          </button>

          {error && (
            <div style={{ marginTop: 12, padding: '10px 14px', background: '#FEE2E2', borderRadius: 8, fontSize: 13, color: '#DC2626' }}>
              {error}
            </div>
          )}
        </div>

        {/* Results */}
        {whatIfResult && (
          <div className="animate-fade-in-up">
            {/* Before / After comparison */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
              {/* Before */}
              <div className="card" style={{ borderTop: '3px solid #E2E8F0' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', marginBottom: 12 }}>BEFORE</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: 48, fontWeight: 800, color: '#1E293B', fontFamily: 'Space Grotesk, sans-serif' }}>
                    {whatIfResult.old_score.score.toFixed(1)}
                  </span>
                  <span style={{ fontSize: 14, color: '#94A3B8' }}>/ 100</span>
                </div>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', padding: '4px 12px',
                  borderRadius: 20, fontSize: 13, fontWeight: 700,
                  background: whatIfResult.old_score.risk_level === 'Low' ? '#DCFCE7' :
                    whatIfResult.old_score.risk_level === 'Medium' ? '#FEF3C7' : '#FEE2E2',
                  color: riskColor(whatIfResult.old_score.risk_level)
                }}>
                  {whatIfResult.old_score.risk_level} Risk
                </div>
              </div>

              {/* After */}
              <div className="card" style={{ borderTop: `3px solid ${scoreChange! > 0 ? '#16A34A' : scoreChange! < 0 ? '#DC2626' : '#E2E8F0'}` }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', marginBottom: 12 }}>
                  AFTER — {whatIfResult.column} {whatIfResult.pct_change > 0 ? '+' : ''}{whatIfResult.pct_change}%
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: 48, fontWeight: 800, fontFamily: 'Space Grotesk, sans-serif',
                    color: scoreChange! > 0 ? '#16A34A' : scoreChange! < 0 ? '#DC2626' : '#1E293B' }}>
                    {whatIfResult.new_score.score.toFixed(1)}
                  </span>
                  <span style={{ fontSize: 14, color: '#94A3B8' }}>/ 100</span>
                  <span style={{ fontSize: 16, fontWeight: 700,
                    color: scoreChange! > 0 ? '#16A34A' : scoreChange! < 0 ? '#DC2626' : '#94A3B8' }}>
                    {scoreChange! > 0 ? '▲' : scoreChange! < 0 ? '▼' : '—'} {Math.abs(scoreChange!).toFixed(1)}
                  </span>
                </div>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', padding: '4px 12px',
                  borderRadius: 20, fontSize: 13, fontWeight: 700,
                  background: whatIfResult.new_score.risk_level === 'Low' ? '#DCFCE7' :
                    whatIfResult.new_score.risk_level === 'Medium' ? '#FEF3C7' : '#FEE2E2',
                  color: riskColor(whatIfResult.new_score.risk_level)
                }}>
                  {whatIfResult.new_score.risk_level} Risk
                  {whatIfResult.old_score.risk_level !== whatIfResult.new_score.risk_level && (
                    <span style={{ marginLeft: 6, fontSize: 10, opacity: 0.8 }}>CHANGED</span>
                  )}
                </div>
              </div>
            </div>

            {/* Sub-score comparison */}
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B', marginBottom: 14 }}>SUB-SCORE COMPARISON</div>
              {[
                { label: 'Data Quality', key: 'data_quality' },
                { label: 'Trend Stability', key: 'trend_stability' },
                { label: 'Risk Inverse', key: 'risk_inverse' },
                { label: 'Opportunity', key: 'opportunity' },
              ].map(sub => {
                const oldVal = whatIfResult.old_score.sub_scores[sub.key as keyof typeof whatIfResult.old_score.sub_scores]
                const newVal = whatIfResult.new_score.sub_scores[sub.key as keyof typeof whatIfResult.new_score.sub_scores]
                const delta = newVal - oldVal
                return (
                  <div key={sub.key} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: '#475569' }}>{sub.label}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 12, color: '#94A3B8' }}>{oldVal.toFixed(1)}</span>
                        <span style={{ fontSize: 12, color: '#94A3B8' }}>→</span>
                        <span style={{ fontSize: 13, fontWeight: 700, color: delta > 0 ? '#16A34A' : delta < 0 ? '#DC2626' : '#1E293B' }}>
                          {newVal.toFixed(1)}
                          {delta !== 0 && <span style={{ fontSize: 11, marginLeft: 4 }}>({delta > 0 ? '+' : ''}{delta.toFixed(1)})</span>}
                        </span>
                      </div>
                    </div>
                    <div style={{ height: 6, background: '#F1F5F9', borderRadius: 3, overflow: 'hidden', position: 'relative' }}>
                      <div style={{ position: 'absolute', height: '100%', background: '#E2E8F0', width: `${oldVal}%`, borderRadius: 3 }} />
                      <div style={{
                        position: 'absolute', height: '100%', borderRadius: 3,
                        background: newVal >= 70 ? '#16A34A' : newVal >= 50 ? '#D97706' : '#DC2626',
                        width: `${newVal}%`, transition: 'width 1s ease', opacity: 0.8
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Scenario Lever Breakdown */}
            {whatIfResult.scenario_deltas && (
              <div className="card" style={{ marginBottom: 20, background: '#F8FAFC' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#64748B' }}>SCENARIO LEVER BREAKDOWN</div>
                  <span style={{
                    fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 12,
                    background: whatIfResult.scenario_deltas.polarity === 'positive' ? '#DCFCE7' :
                                whatIfResult.scenario_deltas.polarity === 'negative' ? '#FEE2E2' : '#F1F5F9',
                    color: whatIfResult.scenario_deltas.polarity === 'positive' ? '#16A34A' :
                           whatIfResult.scenario_deltas.polarity === 'negative' ? '#DC2626' : '#64748B'
                  }}>
                    {whatIfResult.scenario_deltas.polarity === 'positive' && '↑ bigger-is-better'}
                    {whatIfResult.scenario_deltas.polarity === 'negative' && '↓ smaller-is-better'}
                    {whatIfResult.scenario_deltas.polarity === 'neutral' && '– polarity unknown'}
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                  <div style={{ background: 'white', borderRadius: 8, padding: 12, border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#94A3B8', marginBottom: 4 }}>OPPORTUNITY DELTA</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: whatIfResult.scenario_deltas.opportunity_delta > 0 ? '#16A34A' : whatIfResult.scenario_deltas.opportunity_delta < 0 ? '#DC2626' : '#1E293B', fontFamily: 'Space Grotesk, sans-serif' }}>
                      {whatIfResult.scenario_deltas.opportunity_delta > 0 ? '+' : ''}{whatIfResult.scenario_deltas.opportunity_delta.toFixed(1)}
                    </div>
                    <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 2 }}>from column polarity</div>
                  </div>
                  <div style={{ background: 'white', borderRadius: 8, padding: 12, border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#94A3B8', marginBottom: 4 }}>STABILITY PENALTY</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: whatIfResult.scenario_deltas.stability_penalty > 0 ? '#D97706' : '#94A3B8', fontFamily: 'Space Grotesk, sans-serif' }}>
                      −{whatIfResult.scenario_deltas.stability_penalty.toFixed(1)}
                    </div>
                    <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 2 }}>deviation from history</div>
                  </div>
                  <div style={{ background: 'white', borderRadius: 8, padding: 12, border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#94A3B8', marginBottom: 4 }}>RISK PENALTY</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: whatIfResult.scenario_deltas.risk_penalty > 0 ? '#DC2626' : '#94A3B8', fontFamily: 'Space Grotesk, sans-serif' }}>
                      −{whatIfResult.scenario_deltas.risk_penalty.toFixed(1)}
                    </div>
                    <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 2 }}>adverse-direction only</div>
                  </div>
                </div>
                <div style={{ marginTop: 12, padding: '8px 12px', background: 'white', borderRadius: 6, fontSize: 11, color: '#64748B', border: '1px solid #E2E8F0' }}>
                  💡 These levers are deterministic and labeled — the LLM explanation below uses them to explain exactly which forces drove the score change.
                </div>
              </div>
            )}

            {/* Gemini explanation */}
            <div className="card" style={{ background: '#F0FDF4', border: '1px solid #BBF7D0' }}>
              <div style={{ display: 'flex', gap: 10 }}>
                <span style={{ fontSize: 24 }}>✨</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#16A34A', marginBottom: 6 }}>
                    Gemini Analysis — Trend Projection Explanation
                  </div>
                  <p style={{ fontSize: 14, color: '#1E293B', lineHeight: 1.7 }}>
                    {whatIfResult.delta_explanation}
                  </p>
                  <div style={{ marginTop: 10, fontSize: 11, color: '#94A3B8' }}>
                    ⚠ This is a trend projection using scenario simulation math — not a forecast or ML prediction.
                    Results reflect the scoring formula applied to adjusted values.
                  </div>
                </div>
              </div>
            </div>

            {/* Export nudge */}
            <div style={{ marginTop: 20, textAlign: 'center' }}>
              <button className="btn-primary" onClick={handleExport} disabled={exporting} style={{ padding: '12px 28px', fontSize: 15 }}>
                {exporting ? '⏳ Generating PDF...' : '📄 Export Report with This Scenario'}
              </button>
              <p style={{ marginTop: 8, fontSize: 12, color: '#94A3B8' }}>
                PDF includes the what-if section, labeled as Trend Projection
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
