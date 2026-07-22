import { Link, useNavigate } from 'react-router-dom'
import { usePipelineStore, DatasetContext } from '../store/pipelineStore'
import { uploadDemoDataset, getProfile, getSessionData, getSummary, getDecisionScore } from '../lib/api'

export default function Landing() {
  const navigate = useNavigate()
  const store = usePipelineStore()

  const handleDemo = async (
    dataset: 'business_sales' | 'personal_finance' | 'urban_environmental' | 'healthcare_wellness' | 'student_performance',
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

      // Fetch full cleaned rows for dashboard charts (preview is only 5 rows)
      try {
        const dataRes = await getSessionData(uploadData.session_id)
        store.setChartRows(dataRes.rows)
      } catch (e) {
        console.warn('Failed to fetch chart rows', e)
        store.setChartRows([])
      }

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
    <div style={{ minHeight: '100vh', background: '#F8FAFC', color: '#1E293B', fontFamily: 'Outfit, Inter, sans-serif' }}>
      {/* Nav */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 40px', height: 64, background: 'white',
        borderBottom: '1px solid #F1F5F9', position: 'sticky', top: 0, zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, background: '#10B981', borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span style={{ fontWeight: 700, fontSize: 18, color: '#0F172A', letterSpacing: '-0.02em' }}>
            DecisionLens <span style={{ color: '#10B981' }}>AI</span>
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <a href="#how-it-works" className="nav-link" style={{ fontSize: 14, fontWeight: 500, color: '#475569' }}>How it works</a>
          <a href="#architecture" className="nav-link" style={{ fontSize: 14, fontWeight: 500, color: '#475569' }}>Architecture</a>
          <Link to="/upload" className="btn-primary" style={{ padding: '8px 18px', fontSize: 13, background: '#10B981' }}>
            Try Now →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '80px 40px 50px', maxWidth: 1100, margin: '0 auto', textAlign: 'center' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', background: '#ECFDF5', border: '1px solid #A7F3D0',
          borderRadius: 20, marginBottom: 24
        }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981' }}></div>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#047857' }}>
            Gen AI Academy APAC · Powered by Gemini · Hosted on Cloud Run
          </span>
        </div>

        <h1 style={{
          fontSize: 'clamp(36px, 5vw, 60px)',
          fontWeight: 800, color: '#0F172A', lineHeight: 1.15, marginBottom: 20,
          letterSpacing: '-0.03em'
        }}>
          Better Living &<br />
          <span style={{ color: '#10B981' }}>Smarter Communities</span>
        </h1>

        <p style={{ fontSize: 18, color: '#64748B', maxWidth: 640, margin: '0 auto 40px', lineHeight: 1.7 }}>
          An AI-powered Decision Intelligence Platform that helps individuals, communities, and city stakeholders analyze data, answer questions in natural language, generate recommendations, and stress-test decisions before acting — across urban mobility, healthcare access, household finance, education, and more.
        </p>

        <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 40 }}>
          <Link to="/upload" className="btn-primary" style={{ padding: '14px 32px', fontSize: 15, background: '#047857' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 8 }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Upload your CSV / XLSX
          </Link>
          <span style={{ display: 'flex', alignItems: 'center', color: '#94A3B8', fontSize: 14 }}>or pick a demo below</span>
        </div>

        {/* Horizontal Pipeline Stepper */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          gap: 12, flexWrap: 'wrap', padding: '12px 24px', background: 'white',
          borderRadius: 30, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          fontSize: 13, color: '#64748B'
        }}>
          {[
            { label: 'Upload', icon: '📤' },
            { label: 'AI Cleaning', icon: '🧹' },
            { label: 'Profiling', icon: '🔬' },
            { label: 'Decision Score', icon: '🎯' },
            { label: 'Ask the Data', icon: '💬' },
            { label: 'What-If', icon: '🔮' },
            { label: 'PDF Report', icon: '📄' }
          ].map((item, idx) => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>{item.icon}</span>
              <span style={{ fontWeight: 500 }}>{item.label}</span>
              {idx < 6 && <span style={{ color: '#CBD5E1', margin: '0 4px' }}>→</span>}
            </div>
          ))}
        </div>

        {store.step !== 'idle' && store.step !== 'done' && (
          <div style={{ marginTop: 32 }}>
            <div className="status-chip" style={{ margin: '0 auto', background: '#ECFDF5', border: '1px solid #A7F3D0', color: '#047857' }}>
              <div className="dot" style={{ background: '#10B981' }}></div>
              {store.currentStatusLabel}
            </div>
          </div>
        )}

        {store.error && (
          <div style={{ marginTop: 24, padding: '12px 20px', background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: 8, color: '#DC2626', fontSize: 14, maxWidth: 500, margin: '24px auto 0' }}>
            {store.error}
          </div>
        )}
      </section>

      {/* Demo Datasets Grid Section */}
      <section style={{ padding: '60px 40px', background: '#F8FAFC', borderTop: '1px solid #E2E8F0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: '#0F172A', marginBottom: 8 }}>
            Try a demo dataset
          </h2>
          <p style={{ color: '#64748B', fontSize: 14, marginBottom: 32 }}>
            The same pipeline runs across civic, business, and personal data — demonstrating the domain-agnostic scoring engine. Pick one to start.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
            {/* Card 1: Smarter Communities - Urban Air Quality & Mobility */}
            <div className="card" style={{ background: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 24, border: '1px solid #E2E8F0', borderRadius: 12 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <span style={{ fontSize: 24 }}>🏢</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#047857', background: '#E2F0D9', padding: '4px 10px', borderRadius: 12 }}>
                    Smarter Communities
                  </span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>
                  Smarter Communities — Urban Air Quality & Mobility
                </h3>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, marginBottom: 20 }}>
                  24 months of city-wide PM2.5/PM10/NO2 air quality, traffic volume, congestion minutes, 311 citizen complaints, bike trips, transit ridership, tree canopy %, and heat alert days. Use this to read environmental health and test "what if traffic volume drops 15%" scenarios.
                </p>
              </div>
              <button onClick={() => handleDemo('urban_environmental', 'civic')} className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '10px 16px', background: '#F8FAFC', border: '1px solid #E2E8F0', color: '#047857', fontWeight: 600 }}>
                Run pipeline <span>→</span>
              </button>
            </div>

            {/* Card 2: Smarter Communities - Healthcare Access & Wellness */}
            <div className="card" style={{ background: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 24, border: '1px solid #E2E8F0', borderRadius: 12 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <span style={{ fontSize: 24 }}>🩺</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#047857', background: '#E2F0D9', padding: '4px 10px', borderRadius: 12 }}>
                    Smarter Communities
                  </span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>
                  Smarter Communities — Healthcare Access & Wellness
                </h3>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, marginBottom: 20 }}>
                  7 neighborhoods × 4 quarters of clinic availability, average wait times, preventive visit %, emergency visits, telehealth adoption, chronic disease prevalence, and insurance coverage. Use this to read healthcare equity and test "what if clinics within 5km increases by 50%" scenarios.
                </p>
              </div>
              <button onClick={() => handleDemo('healthcare_wellness', 'civic')} className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '10px 16px', background: '#F8FAFC', border: '1px solid #E2E8F0', color: '#047857', fontWeight: 600 }}>
                Run pipeline <span>→</span>
              </button>
            </div>

            {/* Card 3: Small Business - Monthly Sales & Expenses */}
            <div className="card" style={{ background: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 24, border: '1px solid #E2E8F0', borderRadius: 12 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <span style={{ fontSize: 24 }}>📈</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#2563EB', background: '#EFF6FF', padding: '4px 10px', borderRadius: 12 }}>
                    Business
                  </span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>
                  Small Business — Monthly Sales & Expenses
                </h3>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, marginBottom: 20 }}>
                  24 months of revenue, COGS, opex, marketing, customer churn, and net profit for a small B2B SaaS business. Use this to read sales health and test "what if revenue drops 10%" scenarios.
                </p>
              </div>
              <button onClick={() => handleDemo('business_sales', 'business')} className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '10px 16px', background: '#F8FAFC', border: '1px solid #E2E8F0', color: '#2563EB', fontWeight: 600 }}>
                Run pipeline <span>→</span>
              </button>
            </div>

            {/* Card 4: Personal Finance - Household Budget */}
            <div className="card" style={{ background: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 24, border: '1px solid #E2E8F0', borderRadius: 12 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <span style={{ fontSize: 24 }}>💵</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#0D9488', background: '#F0FDFA', padding: '4px 10px', borderRadius: 12 }}>
                    Personal Finance
                  </span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>
                  Personal Finance — Household Budget
                </h3>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, marginBottom: 20 }}>
                  24 months of household income, rent, groceries, dining out, utilities, transport, subscriptions, savings, and entertainment. Use this to read savings health and test "what if I cut dining-out by 20%" scenarios.
                </p>
              </div>
              <button onClick={() => handleDemo('personal_finance', 'personal_finance')} className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '10px 16px', background: '#F8FAFC', border: '1px solid #E2E8F0', color: '#0D9488', fontWeight: 600 }}>
                Run pipeline <span>→</span>
              </button>
            </div>

            {/* Card 5: Student Performance - Grades & Habits */}
            <div className="card" style={{ background: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 24, border: '1px solid #E2E8F0', borderRadius: 12 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <span style={{ fontSize: 24 }}>🎓</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#7C3AED', background: '#F5F3FF', padding: '4px 10px', borderRadius: 12 }}>
                    Student
                  </span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>
                  Student Performance — Grades & Habits
                </h3>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, marginBottom: 20 }}>
                  30 students with attendance %, weekly study hours, assignment / midterm / final scores, sleep, and extracurricular load. Use this to read academic risk and test "what if study hours increase by 5/week" scenarios.
                </p>
              </div>
              <button onClick={() => handleDemo('student_performance', 'student')} className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '10px 16px', background: '#F8FAFC', border: '1px solid #E2E8F0', color: '#7C3AED', fontWeight: 600 }}>
                Run pipeline <span>→</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack Cards */}
      <section id="architecture" style={{ padding: '60px 40px', background: '#F8FAFC', borderTop: '1px solid #E2E8F0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h4 style={{ textTransform: 'uppercase', fontSize: 12, fontWeight: 700, color: '#64748B', letterSpacing: '0.1em', marginBottom: 8 }}>
              Architecture — Free & Open Tech Stack
            </h4>
            <p style={{ color: '#94A3B8', fontSize: 14 }}>Google Cloud GenAI ecosystem · visible in every step, not just the architecture slide</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
            {[
              { title: 'Gemini 3.5 Flash', desc: 'Summary, opportunity scoring, recommendations, what-if narration, AND chat-with-dataset — 6 distinct AI touchpoints via the z-ai-web-dev SDK', badge: 'LLM (FREE TIER)', icon: '✨' },
              { title: 'Cloud Run', desc: 'FastAPI routes deploy to Cloud Run — cold-start-friendly, scales to zero, the live demo URL judges will hit', badge: 'SERVERLESS BACKEND', icon: '☁️' },
              { title: 'Deterministic Profiling', desc: 'dtypes, nulls, IQR outliers, correlation matrix — computed before any Gemini call, so the score is never pure AI vibes', badge: 'PRE-AI STATS', icon: '📊' },
              { title: 'Conversational Analytics', desc: 'Ask the data questions in plain English — Gemini answers using the compact profile JSON, with referenced columns highlighted', badge: 'NATURAL LANGUAGE Q&A', icon: '💬' },
              { title: 'Time-to-Insight Clock', desc: 'A live timer from upload to Decision Score, paired with AI-step status chips surfacing Gemini activity as it happens', badge: 'VISIBLE SPEED', icon: '⚡' },
              { title: 'Explainable AI', desc: 'Every sub-score (Data Quality, Trend Stability, Risk Inverse, Opportunity) shows its weight, value, and rationale — never a black box', badge: 'CLICK-TO-EXPAND', icon: '🧠' }
            ].map(card => (
              <div key={card.title} style={{ padding: 24, background: 'white', borderRadius: 12, border: '1px solid #E2E8F0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <span style={{ fontSize: 24 }}>{card.icon}</span>
                  <div>
                    <h4 style={{ fontSize: 15, fontWeight: 700, color: '#0F172A', margin: 0 }}>{card.title}</h4>
                    <span style={{ fontSize: 9, fontWeight: 700, color: '#64748B', letterSpacing: '0.05em' }}>{card.badge}</span>
                  </div>
                </div>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.5, margin: 0 }}>{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What Makes It Different */}
      <section style={{ padding: '60px 40px', background: '#F8FAFC', borderTop: '1px solid #E2E8F0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h2 style={{ fontSize: 24, fontWeight: 800, color: '#0F172A', marginBottom: 8 }}>
              What makes it different
            </h2>
            <p style={{ color: '#64748B', fontSize: 14 }}>Six capabilities that map directly to the problem statement.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
            {[
              { title: 'Transparent Decision Score', desc: 'A weighted blend of Data Quality, Trend Stability, Risk Inverse, and AI Opportunity sub-scores. Click any sub-score to see the exact formula and rationale — never a black-box number.', icon: '🎯' },
              { title: 'What-If Simulator', desc: 'Pick a column, drag a slider, watch the score and risk level recompute live. Plain-language delta explanations, labeled as \'trend projection\' — never overclaimed as a forecast.', icon: '🎛️' },
              { title: 'Conversational Analytics', desc: 'Ask questions in natural language — \'What correlates with PM2.5?\' or \'Which neighborhood has the worst wait time?\'. Gemini answers using the profiled stats, citing specific columns.', icon: '💬' },
              { title: 'Civic + Personal Use Cases', desc: 'Same pipeline runs on urban air quality, community healthcare access, household budgets, student grades, or business P&L — demonstrating the domain-agnostic scoring engine.', icon: '🏢' },
              { title: '6+ AI Touchpoints', desc: 'Cleaning narration, dataset summary, opportunity scoring, recommendations, what-if narration, AND chat — Gemini is visibly the engine, not a footnote.', icon: '✨' },
              { title: 'Speed as a Feature', desc: 'From upload to Decision Score in under 30 seconds. The Time-to-Insight clock makes the speed advantage visible — manual analysis typically takes 15–30 minutes.', icon: '⚡' }
            ].map(card => (
              <div key={card.title} style={{ padding: 24, background: 'white', borderRadius: 12, border: '1px solid #E2E8F0' }}>
                <span style={{ fontSize: 24, display: 'block', marginBottom: 12 }}>{card.icon}</span>
                <h4 style={{ fontSize: 15, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>{card.title}</h4>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.5, margin: 0 }}>{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Problem Statement Alignment */}
      <section style={{ padding: '60px 40px', background: '#F8FAFC', borderTop: '1px solid #E2E8F0', borderBottom: '1px solid #E2E8F0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h4 style={{ textTransform: 'uppercase', fontSize: 12, fontWeight: 700, color: '#64748B', letterSpacing: '0.1em', marginBottom: 8 }}>
              Problem Statement Alignment
            </h4>
            <p style={{ color: '#94A3B8', fontSize: 14 }}>Gen Al Academy APAC · "AI for Better Living and Smarter Communities"</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            {[
              { title: 'URBAN MOBILITY', desc: 'Air quality + traffic + transit + 311 complaints dataset' },
              { title: 'HEALTHCARE ACCESS', desc: 'Clinic availability + wait times + chronic disease prevalence dataset' },
              { title: 'ENVIRONMENTAL SUSTAINABILITY', desc: 'Tree canopy, PM2.5/PM10/NO2 tracking, heat alert days' },
              { title: 'CITIZEN ENGAGEMENT', desc: '311 citizen complaints tracked and correlated with service quality' }
            ].map(col => (
              <div key={col.title} style={{ padding: 20, background: 'white', borderRadius: 8, border: '1px solid #E2E8F0' }}>
                <h5 style={{ fontSize: 12, fontWeight: 700, color: '#047857', marginTop: 0, marginBottom: 8, letterSpacing: '0.02em' }}>{col.title}</h5>
                <p style={{ fontSize: 12, color: '#64748B', lineHeight: 1.4, margin: 0 }}>{col.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '32px 40px', background: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <span style={{ fontSize: 13, color: '#64748B' }}>
          DecisionLens AI · Made with ❤️ by Nawang Dorjay
        </span>
        <div style={{ display: 'flex', gap: 12 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: '#64748B', background: '#F1F5F9', padding: '4px 10px', borderRadius: 12 }}>
            Powered by Gemini 3.5 Flash
          </span>
          <span style={{ fontSize: 11, fontWeight: 600, color: '#64748B', background: '#F1F5F9', padding: '4px 10px', borderRadius: 12 }}>
            Hosted on Cloud Run
          </span>
        </div>
      </footer>
    </div>
  )
}
