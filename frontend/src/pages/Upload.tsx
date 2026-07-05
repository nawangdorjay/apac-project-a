import { useState, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { usePipelineStore, DatasetContext } from '../store/pipelineStore'
import { uploadFile, uploadDemoDataset, getProfile, getSummary, getDecisionScore } from '../lib/api'

const CONTEXT_OPTIONS: { value: DatasetContext; label: string; icon: string }[] = [
  { value: 'business', label: 'Business', icon: '📈' },
  { value: 'personal_finance', label: 'Personal Finance', icon: '💰' },
  { value: 'student', label: 'Student / Academic', icon: '📚' },
]

export default function Upload() {
  const navigate = useNavigate()
  const store = usePipelineStore()
  const [selectedContext, setSelectedContext] = useState<DatasetContext>('business')
  const [isProcessing, setIsProcessing] = useState(false)
  const [thoughtStream, setThoughtStream] = useState<string[]>([])

  const runPipeline = async (sessionId: string) => {
    // 1. Profiling
    store.setStep('profiling', 'Profiling columns...')
    setThoughtStream(prev => [...prev, '⚙️ Initializing local data profiling engine...'])
    const profileData = await getProfile(sessionId)
    store.setProfileData(profileData)
    setThoughtStream(prev => [...prev, `📊 Checked dataset structure: profiled ${profileData.columns.length} columns.`])
    await new Promise(r => setTimeout(r, 450))

    // 2. Summarization
    store.setStep('summarizing', 'Gemini 2.0 Flash generating summary narrative...')
    setThoughtStream(prev => [...prev, '✨ Connecting to Google GenAI API...'])
    await new Promise(r => setTimeout(r, 450))
    setThoughtStream(prev => [...prev, '🚀 Transmitting profiling stats to gemini-2.0-flash...'])
    const summaryData = await getSummary(sessionId)
    store.setSummaryData(summaryData)
    setThoughtStream(prev => [...prev, '📝 Gemini narrative summary generated successfully!'])
    await new Promise(r => setTimeout(r, 450))

    // 3. Scoring
    store.setStep('scoring', 'Gemini analyzing opportunity signals...')
    setThoughtStream(prev => [...prev, '⚖️ Computing deterministic Data Quality, Trend, and Risk scores...'])
    await new Promise(r => setTimeout(r, 450))
    setThoughtStream(prev => [...prev, '🎯 Requesting Gemini to evaluate opportunity signals...'])
    const scoreData = await getDecisionScore(sessionId)
    store.setScoreData(scoreData)
    setThoughtStream(prev => [...prev, '🏆 Full Decision Score computed (Capped AI weight 15%).'])
    await new Promise(r => setTimeout(r, 600))

    store.setStep('done')
    navigate('/results')
  }

  const processFile = async (file: File) => {
    if (isProcessing) return
    setIsProcessing(true)
    store.reset()
    setThoughtStream([])
    store.setDatasetContext(selectedContext)
    store.startClock()

    try {
      store.setStep('uploading', 'Uploading and validating file...')
      const data = await uploadFile(file, selectedContext)
      store.setSessionId(data.session_id)
      store.setFilename(data.filename)
      store.setRapidsActive(!!data.rapids_active)

      store.setStep('cleaning', 'Cleaning data...')
      await new Promise(r => setTimeout(r, 600)) // let user see cleaning step
      store.setCleaningLog(data.cleaning_log, data.rows_before, data.rows_after)
      store.setPreviewRows(data.preview_rows)

      await runPipeline(data.session_id)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      store.setError(message)
      store.setStep('idle')
      setIsProcessing(false)
    }
  }

  const processDemo = async (dataset: string, context: DatasetContext) => {
    if (isProcessing) return
    setIsProcessing(true)
    store.reset()
    setThoughtStream([])
    store.setDatasetContext(context)
    store.startClock()

    try {
      store.setStep('uploading', `Loading ${dataset === 'business_sales' ? 'business' : 'personal finance'} dataset...`)
      const data = await uploadDemoDataset(dataset, context)
      store.setSessionId(data.session_id)
      store.setFilename(data.filename)
      store.setRapidsActive(!!data.rapids_active)

      store.setStep('cleaning', 'Cleaning data...')
      await new Promise(r => setTimeout(r, 400))
      store.setCleaningLog(data.cleaning_log, data.rows_before, data.rows_after)
      store.setPreviewRows(data.preview_rows)

      await runPipeline(data.session_id)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load demo'
      store.setError(message)
      store.setStep('idle')
      setIsProcessing(false)
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      processFile(acceptedFiles[0])
    }
  }, [selectedContext])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxFiles: 1,
    disabled: isProcessing,
  })

  const stepLabels = [
    { key: 'uploading', label: 'Uploading', icon: '📤' },
    { key: 'cleaning', label: 'Cleaning Data', icon: '🧹' },
    { key: 'profiling', label: 'Profiling Columns', icon: '🔬' },
    { key: 'summarizing', label: 'Gemini Summary', icon: '✨' },
    { key: 'scoring', label: 'Decision Score', icon: '🎯' },
  ]

  const currentStepIdx = stepLabels.findIndex(s => s.key === store.step)

  return (
    <div style={{ minHeight: '100vh', background: '#F8FAFC' }}>
      {/* Nav */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 40px', height: 60, background: 'white', borderBottom: '1px solid #E2E8F0'
      }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div style={{ width: 28, height: 28, background: '#2563EB', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          <span style={{ fontFamily: 'Space Grotesk, sans-serif', fontWeight: 700, fontSize: 15, color: '#1E293B' }}>DecisionLens AI</span>
        </Link>
        <Link to="/" className="btn-ghost">← Back</Link>
      </nav>

      <div style={{ maxWidth: 700, margin: '0 auto', padding: '24px 24px' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 26, fontWeight: 700, color: '#1E293B', marginBottom: 6 }}>
            Upload Your Data
          </h1>
          <p style={{ color: '#64748B', fontSize: 14 }}>
            CSV or XLSX — we'll clean, profile, and score it automatically
          </p>
        </div>

        {/* Dataset context selector */}
        {!isProcessing && (
          <div className="card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#64748B', marginBottom: 10 }}>
              DATASET TYPE
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              {CONTEXT_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => setSelectedContext(opt.value)} style={{
                  flex: 1, padding: '8px 6px', border: `2px solid ${selectedContext === opt.value ? '#2563EB' : '#E2E8F0'}`,
                  borderRadius: 8, background: selectedContext === opt.value ? '#EFF6FF' : 'white',
                  cursor: 'pointer', fontSize: 13, fontWeight: 500,
                  color: selectedContext === opt.value ? '#1D4ED8' : '#64748B',
                  transition: 'all 0.15s', textAlign: 'center'
                }}>
                  <div style={{ fontSize: 18, marginBottom: 2 }}>{opt.icon}</div>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Drop zone */}
        {!isProcessing && (
          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'active' : ''}`}
            style={{ padding: '32px 24px', textAlign: 'center', marginBottom: 16 }}
          >
            <input {...getInputProps()} />
            <div style={{ fontSize: 40, marginBottom: 12 }}>📁</div>
            {isDragActive ? (
              <p style={{ fontSize: 15, fontWeight: 600, color: '#2563EB' }}>Drop it here!</p>
            ) : (
              <>
                <p style={{ fontSize: 15, fontWeight: 600, color: '#1E293B', marginBottom: 6 }}>
                  Drag & drop your CSV or XLSX
                </p>
                <p style={{ fontSize: 12, color: '#94A3B8', marginBottom: 16 }}>
                  or click to browse — max 50MB
                </p>
                <button className="btn-primary" style={{ padding: '8px 16px', fontSize: 13 }}>Choose File</button>
              </>
            )}
          </div>
        )}

        {/* Demo dataset buttons */}
        {!isProcessing && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: '#94A3B8', marginBottom: 12 }}>OR TRY A DEMO DATASET</div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button className="btn-secondary" onClick={() => processDemo('business_sales', 'business')}>
                📈 Business Sales Demo
              </button>
              <button className="btn-secondary" onClick={() => processDemo('personal_finance', 'personal_finance')}>
                💰 Personal Finance Demo
              </button>
              <button className="btn-secondary" style={{ borderColor: '#10B981', color: '#059669' }} onClick={() => processDemo('urban_environmental', 'student')}>
                🏙️ Smart Communities Demo
              </button>
            </div>
          </div>
        )}

        {/* Processing progress */}
        {isProcessing && (
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1E293B', marginBottom: 20, textAlign: 'center' }}>
              Running Pipeline...
            </div>

            {/* Step progress */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
              {stepLabels.map((s, i) => {
                const isDone = currentStepIdx > i
                const isCurrent = currentStepIdx === i
                return (
                  <div key={s.key} className={isCurrent ? 'animate-slide-in' : ''} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    opacity: isDone ? 1 : isCurrent ? 1 : 0.3,
                    transition: 'opacity 0.3s'
                  }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                      background: isDone ? '#DCFCE7' : isCurrent ? '#EFF6FF' : '#F1F5F9',
                      border: `2px solid ${isDone ? '#16A34A' : isCurrent ? '#2563EB' : '#E2E8F0'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14
                    }}>
                      {isDone ? '✓' : s.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#1E293B' }}>{s.label}</div>
                      {isCurrent && (
                        <div style={{ fontSize: 12, color: '#2563EB' }}>{store.currentStatusLabel}</div>
                      )}
                    </div>
                    {isCurrent && (
                      <div className="status-chip" style={{ marginLeft: 'auto' }}>
                        <div className="dot"></div>
                        Running
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Cleaning log preview */}
            {store.cleaningLog.length > 0 && (
              <div style={{ background: '#F8FAFC', borderRadius: 8, padding: '12px 16px', marginBottom: thoughtStream.length > 0 ? 12 : 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#64748B', marginBottom: 8 }}>CLEANING LOG</div>
                {store.cleaningLog.map((log, i) => (
                  <div key={i} className="check-item" style={{ animationDelay: `${i * 0.1}s` }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 13, color: '#475569' }}>
                      <span style={{ color: '#16A34A', fontWeight: 700 }}>✓</span>
                      {log}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Thought Stream terminal-like output */}
            {thoughtStream.length > 0 && (
              <div style={{
                background: '#1E293B', borderRadius: 8, padding: '12px 16px',
                fontFamily: 'monospace', fontSize: 12, color: '#38BDF8',
                maxHeight: 180, overflowY: 'auto', border: '1px solid #334155', textAlign: 'left'
              }}>
                <div style={{ color: '#94A3B8', fontSize: 10, fontWeight: 700, marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                  <span>AI REASONING LOG</span>
                  <span style={{ color: '#34D399', animation: 'pulse 1.5s infinite' }}>● LIVE ACTION TIMELINE</span>
                </div>
                {thoughtStream.map((t, idx) => (
                  <div key={idx} style={{ marginBottom: 4, lineHeight: 1.4 }}>
                    <span style={{ color: '#64748B' }}>&gt;</span> {t}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {store.error && (
          <div style={{ padding: '12px 16px', background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: 8, color: '#DC2626', fontSize: 14 }}>
            <strong>Error:</strong> {store.error}
          </div>
        )}
      </div>
    </div>
  )
}
