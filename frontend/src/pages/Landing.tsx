import { Link, useNavigate } from 'react-router-dom'
import { usePipelineStore, DatasetContext } from '../store/pipelineStore'
import { uploadDemoDataset, getProfile, getSummary, getDecisionScore } from '../lib/api'

export default function Landing() {
  const navigate = useNavigate()
  const store = usePipelineStore()

  const handleDemo = async (
    dataset: 'business_sales' | 'personal_finance' | 'urban_environmental',
    context: DatasetContext
  ) => {
    store.reset()
    store.setDatasetContext(context)
    store.startClock()
    store.setStep('uploading', 'Loading demo dataset...')

    try {
      // Upload
      const uploadData = await uploadDemoDataset(dataset, context)
      store.setSessionId(uploadData.session_id)
      store.setFilename(uploadData.filename)
      store.setCleaningLog(uploadData.cleaning_log, uploadData.rows_before, uploadData.rows_after)
      store.setPreviewRows(uploadData.preview_rows)
      store.setRapidsActive(!!uploadData.rapids_active)
      store.setStep('profiling', 'Profiling data...')

      // Profile
      const profileData = await getProfile(uploadData.session_id)
      store.setProfileData(profileData)
      store.setStep('summarizing', 'Gemini 2.0 Flash generating summary...')

      // Summary
      const summaryData = await getSummary(uploadData.session_id)
      store.setSummaryData(summaryData)
      store.setStep('scoring', 'Computing Decision Score...')

      // Score
      const scoreData = await getDecisionScore(uploadData.session_id)
      store.setScoreData(scoreData)
      store.setStep('done')

      navigate('/results')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load demo'
      store.setError(message)
      store.setStep('idle')
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F8FAFC' }}>
      {/* Nav */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 40px', height: 60, background: 'white',
        borderBottom: '1px solid #E2E8F0', position: 'sticky', top: 0, zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, background: '#2563EB', borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span style={{ fontFamily: 'Space Grotesk, sans-serif', fontWeight: 700, fontSize: 17, color: '#1E293B' }}>
            DecisionLens AI
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <a href="#how-it-works" className="nav-link">How it works</a>
          <a href="#architecture" className="nav-link">Architecture</a>
          <Link to="/upload" className="btn-primary" style={{ padding: '8px 18px', fontSize: 13 }}>
            Try Now →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '80px 40px 60px', maxWidth: 1100, margin: '0 auto', textAlign: 'center' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', background: '#EFF6FF', border: '1px solid #BFDBFE',
          borderRadius: 20, marginBottom: 24
        }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#2563EB' }}></div>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#1D4ED8' }}>
            Powered by Google Gemini · Cloud Run · APAC GenAI Hackathon
          </span>
        </div>

        <h1 style={{
          fontFamily: 'Space Grotesk, sans-serif',
          fontSize: 'clamp(36px, 5vw, 60px)',
          fontWeight: 700, color: '#1E293B', lineHeight: 1.15, marginBottom: 20
        }}>
          From Data to Decisions<br />
          <span style={{ color: '#2563EB' }}>in Seconds</span>
        </h1>

        <p style={{ fontSize: 18, color: '#64748B', maxWidth: 560, margin: '0 auto 40px', lineHeight: 1.7 }}>
          Upload any CSV or spreadsheet. Get an AI-powered <strong>Decision Score</strong>, 
          interactive dashboard, and scenario simulation — not just a chart.
        </p>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to="/upload" className="btn-primary" style={{ padding: '13px 28px', fontSize: 15 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Upload Your Data
          </Link>
          <button onClick={() => handleDemo('business_sales', 'business')} className="btn-secondary" style={{ padding: '13px 28px', fontSize: 15 }}>
            Try Business Demo
          </button>
          <button onClick={() => handleDemo('personal_finance', 'personal_finance')} className="btn-secondary" style={{ padding: '13px 28px', fontSize: 15 }}>
            Try Personal Finance Demo
          </button>
          <button onClick={() => handleDemo('urban_environmental', 'student')} className="btn-primary" style={{ padding: '13px 28px', fontSize: 15, background: '#10B981' }}>
            ⚡ Try Smart Community Demo
          </button>
        </div>

        {store.step !== 'idle' && store.step !== 'done' && (
          <div style={{ marginTop: 24 }}>
            <div className="status-chip" style={{ margin: '0 auto' }}>
              <div className="dot"></div>
              {store.currentStatusLabel}
            </div>
          </div>
        )}

        {store.error && (
          <div style={{ marginTop: 16, padding: '12px 20px', background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: 8, color: '#DC2626', fontSize: 14 }}>
            {store.error}
          </div>
        )}
      </section>

      {/* Stats bar */}
      <section style={{ background: 'white', borderTop: '1px solid #E2E8F0', borderBottom: '1px solid #E2E8F0', padding: '20px 40px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: 20 }}>
          {[
            { label: 'Avg. Time to Insight', value: '< 60s', sub: 'vs 15–30 min manually' },
            { label: 'AI Touchpoints', value: '5+', sub: 'Gemini calls per analysis' },
            { label: 'Decision Score', value: '0–100', sub: 'Transparent, explainable' },
            { label: 'Data Types', value: 'Any CSV/XLSX', sub: 'Business, finance, academic' },
          ].map(stat => (
            <div key={stat.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#1E293B', fontFamily: 'Space Grotesk, sans-serif' }}>{stat.value}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#64748B', marginTop: 2 }}>{stat.label}</div>
              <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 1 }}>{stat.sub}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" style={{ padding: '70px 40px', maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 32, fontWeight: 700, color: '#1E293B', marginBottom: 10 }}>
            The Full Pipeline
          </h2>
          <p style={{ color: '#64748B', fontSize: 15 }}>Every step is visible — no black boxes</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          {[
            { step: '01', title: 'Upload', desc: 'CSV or XLSX — or pick a demo dataset', icon: '📤', color: '#EFF6FF', border: '#BFDBFE' },
            { step: '02', title: 'Clean', desc: 'Dedupe, nulls, type coercion — visible log', icon: '🧹', color: '#F0FDF4', border: '#BBF7D0' },
            { step: '03', title: 'Profile', desc: 'Pandas stats: types, outliers, correlations', icon: '🔬', color: '#FFF7ED', border: '#FED7AA' },
            { step: '04', title: 'Dashboard', desc: 'Auto-selected charts per column type', icon: '📊', color: '#FAF5FF', border: '#E9D5FF' },
            { step: '05', title: 'AI Summary', desc: 'Gemini narrates your dataset in plain English', icon: '✨', color: '#EFF6FF', border: '#BFDBFE' },
            { step: '06', title: 'Decision Score', desc: '0–100 score with transparent breakdown', icon: '🎯', color: '#F0FDF4', border: '#BBF7D0' },
            { step: '07', title: 'What-If', desc: 'Simulate scenarios before you act', icon: '🔮', color: '#FFF1F2', border: '#FECDD3' },
            { step: '08', title: 'PDF Report', desc: 'One-click executive export with what-if included', icon: '📄', color: '#F8FAFC', border: '#E2E8F0' },
          ].map(item => (
            <div key={item.step} className="card-sm" style={{ background: item.color, border: `1px solid ${item.border}` }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>{item.icon}</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', marginBottom: 4 }}>STEP {item.step}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#1E293B', marginBottom: 4 }}>{item.title}</div>
              <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.5 }}>{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture */}
      <section id="architecture" style={{ background: '#1E293B', padding: '60px 40px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: 'white', marginBottom: 10 }}>
              Architecture
            </h2>
            <p style={{ color: '#94A3B8', fontSize: 14 }}>Built on Google Cloud — Gemini + Cloud Run at the center</p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, flexWrap: 'wrap' }}>
            {[
              { label: 'React + Vite', sub: 'Frontend (Vercel)', icon: '⚛️', color: '#1D4ED8' },
              { label: '→', sub: '', icon: '', color: 'transparent' },
              { label: 'FastAPI', sub: '☁ Google Cloud Run', icon: '🐍', color: '#16A34A' },
              { label: '→', sub: '', icon: '', color: 'transparent' },
              { label: 'NVIDIA RAPIDS', sub: 'cuDF GPU Acceleration', icon: '⚡', color: '#76B900' },
              { label: '→', sub: '', icon: '', color: 'transparent' },
              { label: 'Gemini 2.0 Flash', sub: 'AI Engine', icon: '✨', color: '#7C3AED' },
            ].map((item, i) => (
              item.label === '→' ? (
                <span key={i} style={{ fontSize: 24, color: '#475569' }}>→</span>
              ) : (
                <div key={i} style={{
                  padding: '16px 24px', background: '#334155', borderRadius: 10,
                  border: `1px solid ${item.color}40`, textAlign: 'center', minWidth: 140
                }}>
                  <div style={{ fontSize: 28, marginBottom: 6 }}>{item.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'white', marginBottom: 2 }}>{item.label}</div>
                  <div style={{ fontSize: 11, color: '#94A3B8' }}>{item.sub}</div>
                </div>
              )
            ))}
          </div>

          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <p style={{ color: '#64748B', fontSize: 12 }}>
              All Gemini calls use structured JSON output · Raw data never sent to AI · Deterministic scoring formula
            </p>
          </div>
        </div>
      </section>

      {/* Dataset picker CTA */}
      <section style={{ padding: '60px 40px', maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
        <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#1E293B', marginBottom: 12 }}>
          Try it now — pick a demo dataset
        </h2>
        <p style={{ color: '#64748B', marginBottom: 32, fontSize: 15 }}>
          Same pipeline, same scoring engine — just different contexts
        </p>
        <div style={{ display: 'flex', gap: 20, justifyContent: 'center', flexWrap: 'wrap' }}>
          <div className="card" style={{ maxWidth: 280, textAlign: 'left', cursor: 'pointer' }} onClick={() => handleDemo('business_sales', 'business')}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📈</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1E293B', marginBottom: 6 }}>Business Sales</div>
            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 16 }}>
              Monthly revenue, expenses, profit & customers. Decision Score on business health.
            </div>
            <div style={{ fontSize: 12, color: '#64748B' }}>Example what-if: <em>"Revenue drops 10%?"</em></div>
            <button className="btn-primary" style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
              Try Business Demo →
            </button>
          </div>

          <div className="card" style={{ maxWidth: 280, textAlign: 'left', cursor: 'pointer' }} onClick={() => handleDemo('personal_finance', 'personal_finance')}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>💰</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1E293B', marginBottom: 6 }}>Personal Finance</div>
            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 16 }}>
              Monthly income vs. spending by category. Decision Score on savings health.
            </div>
            <div style={{ fontSize: 12, color: '#64748B' }}>Example what-if: <em>"Cut dining-out 20%?"</em></div>
            <button className="btn-primary" style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
              Try Finance Demo →
            </button>
          </div>

          <div className="card" style={{ maxWidth: 280, textAlign: 'left', cursor: 'pointer' }} onClick={() => handleDemo('urban_environmental', 'student')}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>🏙️</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1E293B', marginBottom: 6 }}>Smart Communities</div>
            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 16 }}>
              Air quality, traffic, municipal energy & public services. Decision Score on community wellness.
            </div>
            <div style={{ fontSize: 12, color: '#64748B' }}>Example what-if: <em>"Traffic Delay drops 20%?"</em></div>
            <button className="btn-primary" style={{ marginTop: 16, width: '100%', justifyContent: 'center', background: '#10B981' }}>
              Try Community Demo →
            </button>
          </div>

          <div className="card" style={{ maxWidth: 280, textAlign: 'left', opacity: 0.7 }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📚</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1E293B', marginBottom: 6 }}>Your Own Data</div>
            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 16 }}>
              Upload any CSV or XLSX. The pipeline adapts to your data automatically.
            </div>
            <div style={{ fontSize: 12, color: '#64748B' }}>Supports: CSV, XLSX, XLS</div>
            <Link to="/upload" className="btn-secondary" style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
              Upload File →
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid #E2E8F0', padding: '24px 40px', textAlign: 'center' }}>
        <p style={{ fontSize: 13, color: '#94A3B8' }}>
          DecisionLens AI · Built by Mind_Mesh (Nawang Dorjay, Sayan Kundu, Twisha, Swayam) · APAC GenAI Hackathon 2026
        </p>
      </footer>
    </div>
  )
}
