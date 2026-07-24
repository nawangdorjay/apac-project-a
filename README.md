# 🏙️ DecisionLens AI

> **Decision Intelligence & Scenario Simulation Platform for Smart Communities**  
> Built for the *Google GenAI Academy APAC Hackathon* 🚀

[![Frontend Live](https://img.shields.io/badge/Frontend-Vercel%20Live-brightgreen?style=for-the-badge&logo=vercel)](https://frontend-iota-one-33.vercel.app)
[![API Docs](https://img.shields.io/badge/API%20Docs-Render%20Live-blue?style=for-the-badge&logo=fastapi)](https://decision-lens-apac.onrender.com/docs)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM%20Active-76B900?style=for-the-badge&logo=nvidia)](https://build.nvidia.com)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%20Active-8E75C2?style=for-the-badge&logo=google-gemini)](https://aistudio.google.com)

> ⚠️ **Note for Hackathon Reviewers:**  
> The backend of this platform is deployed on **Render's Free Tier**. Render sleeps containers after ~15 min of inactivity — the first request after sleep takes 30–60s to respond while uvicorn boots. **We've built three layers of mitigation so you should rarely notice this:**
> 
> 1. **Vercel Cron keep-alive** — every 5 minutes, a Vercel Serverless Function pings `/api/warmup` to keep the container awake between judge visits.
> 2. **Frontend warmup ping** — when you load the landing page, the frontend fires a background `/api/warmup` request. By the time you click a demo button, the backend is already booted.
> 3. **Cold-start aware API client** — if the first real request still times out, the client automatically retries once after 3s and shows a "Waking up the backend" banner so you know what's happening.
> 
> If you do see the banner, just wait ~30s — the request will complete automatically. Subsequent requests will be instant.

---

## 🔗 Live Deployments

*   **⚡ Deployed Frontend (React):** [https://frontend-iota-one-33.vercel.app](https://frontend-iota-one-33.vercel.app)
*   **📡 Deployed Backend API (FastAPI):** [https://decision-lens-apac.onrender.com](https://decision-lens-apac.onrender.com)
*   **📖 Swagger API Docs:** [https://decision-lens-apac.onrender.com/docs](https://decision-lens-apac.onrender.com/docs)

---

## 🌟 Key Features

1.  **🧹 Automated Data Cleaning & Profiling:** 
    Resolves duplicates, normalizes null values (median/mode fill), sanitizes inputs, and builds column profiles (cardinality, correlations, outlier counts).
2.  **⚖️ Transparent Decision Intelligence Scorer:** 
    Calculates an objective, deterministic score (0–100) combining Data Quality, Trend Metrics, and Risk Ratios, blended with a capped (15% max weight) Gemini-derived opportunity index to prevent AI bias. Every sub-score ships with a **per-component math breakdown** (formula + raw values + weights) accessible via the "🧮 Show Full Math" modal — no black boxes.
3.  **🎛️ "What-If" Scenario Simulator:** 
    Interact with sliders to test perturbations (e.g. increase public transit ridership by 30%), recompute the scoring formula instantly, and receive real-time, plain-language impacts narrated by the LLM. Includes a **"SCENARIO LEVER BREAKDOWN"** card showing exactly which forces (Opportunity Δ, Stability Penalty, Risk Penalty) drove the score change.
4.  **⚖️ Side-by-Side Scenario Comparison:** 
    Run two scenarios simultaneously (e.g. "Revenue +10% vs Expenses −10%") and see which produces a better score. Pure math — no LLM call — so it's instant (~24ms). Winner badge + sub-score delta table. Click "Use Scenario X → Get Gemini analysis" to drill into the winner with a narrative explanation.
5.  **🛡️ 4-Tier Redundant LLM Failover System:** 
    Bulletproof routing engine that guarantees API uptime during high traffic or quota exhaustions:
    $$\text{Gemini API (Cloud)} \longrightarrow \text{NVIDIA NIM (Cloud)} \longrightarrow \text{Ollama (Local/Network)} \longrightarrow \text{Mock Templates (Local)}$$
    A **live LLM tier badge** in the nav shows which tier answered the most recent call, plus circuit breaker state and cache/RPM stats — judges can SEE the failover happening.
6.  **🖨️ PDF Executive Report Generator:** 
    Export clean, print-ready ReportLab-generated PDF files with **embedded visual charts**: semicircle score gauge, colored sub-score bars, and what-if lever breakdown chart. No longer text-only.
7.  **💾 Session Persistence:** 
    Sessions are stored in SQLite (not in-memory), so a page refresh or Render backend restart mid-demo recovers your full state automatically via `/api/restore`. No more "Session not found" dead-ends.
8.  **⚡ NVIDIA cuDF Acceleration:** 
    Integrates zero-code-change GPU acceleration. Uses RAPIDS `cudf.pandas` if hosted on a CUDA-supported environment, failing back seamlessly to CPU pandas.
9.  **🤖 Conversational Analytics:** 
    Ask questions in plain English ("What correlates with PM2.5?" or "Which neighborhood has the worst wait time?"). Gemini answers using the compact profile JSON, citing specific columns. Raw data never leaves the server.
10. **🔮 Linear Trend Projection:** 
    Least-squares fit on any numeric column, projected forward 3 periods with 95% CI bands. Honestly labeled as "naive extrapolation" — not an ML forecast.

---

## 🏗️ System Architecture

```
┌───────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Frontend          │────▶│  FastAPI      │────▶│  Cloud & Local LLMs │
│  React + Vite     │    │  (Backend)   │     │  - Gemini 2.0 Flash │
│  Tailwind CSS     │    └──────┬───────┘     │  - NVIDIA NIM       │
│  Recharts         │           │             │  - Ollama (Llama3)  │
└───────────────────┘           ▼             └─────────────────────┘
                      ┌───────────────────┐
                      │   NVIDIA RAPIDS   │   (Loads cudf.pandas if available)
                      │   GPU Accelerator │
                      └───────────────────┘
```

---

## 🛠️ Tech Stack

*   **Frontend:** Vite, React, TypeScript, Tailwind CSS, Recharts, Zustand, Axios.
*   **Backend:** FastAPI, Pandas, NumPy, OpenPyXL, ReportLab, Matplotlib, Google GenAI SDK, SQLite (session persistence).
*   **LLM Stack:** Google Gemini 2.0 Flash (primary), NVIDIA NIM `meta/llama-3.1-8b-instruct` (fallback 1), Ollama (fallback 2), Mock Templates (fallback 3).
*   **Hosting:** Vercel (Frontend + Cron), Render (Backend / Dockerized).

---

## 📋 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Root — API info + RAPIDS status |
| GET | `/health` | Health check |
| GET | `/api/warmup` | Lightweight keep-alive ping (for Vercel Cron) |
| POST | `/api/upload` | Upload CSV/XLSX or select demo dataset → returns session_id |
| GET | `/api/data/{session_id}` | Full cleaned rows (for dashboard charts) |
| GET | `/api/profile/{session_id}` | Deterministic column profiling (dtypes, nulls, outliers, correlations) |
| POST | `/api/summary/{session_id}` | Gemini narrative summary + key findings |
| POST | `/api/decision-score/{session_id}` | Decision Score + sub-scores + recommendations + math breakdown |
| POST | `/api/whatif/{session_id}` | Single scenario simulation |
| POST | `/api/whatif/compare/{session_id}` | Side-by-side scenario comparison (no LLM call) |
| POST | `/api/report/{session_id}` | Generate PDF with embedded charts |
| POST | `/api/chat/{session_id}` | Conversational Q&A with dataset |
| GET | `/api/forecast/{session_id}` | Linear trend projection (naive extrapolation) |
| POST | `/api/automate/{session_id}` | Simulated workflow automation trigger |
| GET | `/api/restore/{session_id}` | Rebuild frontend state after refresh/restart |
| GET | `/api/llm-status` | Live 4-tier failover state + circuit breaker + cache stats |
| GET | `/api/sessions/count` | Admin: persisted session count |

Full interactive docs at `/docs` (Swagger UI).

---

## ⚠️ Known Limitations

We believe in being honest about what this is and isn't:

1.  **Render free-tier cold starts:** Despite our 5-layer mitigation, the first request after 15+ min of inactivity may still take 30–60s. The cold-start banner will tell you when this is happening.
2.  **Trend projection is naive:** The `/api/forecast` endpoint uses simple least-squares linear extrapolation — not an ML model. It assumes the historical trend continues unchanged and cannot predict shocks, seasonality, or regime changes. We label it honestly as "linear extrapolation" throughout the UI.
3.  **Opportunity sub-score is AI-derived:** The only non-deterministic component of the Decision Score is the Opportunity sub-score (capped at 15% weight). Everything else is pure math computed from dataset statistics.
4.  **Sessions have a 24h TTL:** SQLite sessions are cleaned up after 24 hours to prevent the DB from growing forever. Active demos are not affected.
5.  **Column polarity is hardcoded:** The What-If simulator uses a predefined `POSITIVE_COLUMNS` / `NEGATIVE_COLUMNS` set to determine direction-aware deltas. Columns not in either set are treated as "neutral" (only stability penalty applies). Future versions could infer polarity from column semantics.
6.  **No authentication:** This is a hackathon demo. Anyone with the URL can use it. Don't upload sensitive data.

---

## 💻 Local Quickstart

### 1. Run Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Run Frontend
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser!

---

## 🛡️ Cold-Start Mitigation (Render Free Tier)

Render's free tier sleeps containers after ~15 min of inactivity. The first request after sleep takes 30–60s while uvicorn boots. We mitigate this with **four layers** (the fifth — Vercel Cron — is optional and requires a Pro plan):

| Layer | What it does | Where |
|-------|--------------|-------|
| **1. Frontend warmup** | On Landing page mount, the client fires a background `GET /api/warmup` so the backend is booted before the user clicks anything. | `frontend/src/lib/api.ts` `warmupBackend()` + `Landing.tsx` |
| **2. Cold-start aware client** | All API calls go through `coldStartRequest()` which uses a 90s timeout on first call, retries once on network/timeout error, and surfaces state via `BackendWarmth` listeners. | `frontend/src/lib/api.ts` |
| **3. ColdStartLoader banner** | When warmth is `warming` or `cold`, a dismissible banner appears at the top: "Waking up the backend — first request after inactivity takes ~30–60s on Render free tier". | `frontend/src/components/ColdStartLoader.tsx` |
| **4. LLM badge cold-start state** | The `LlmStatusBadge` turns amber and pulses when the backend is cold-starting, so judges see we're aware of it. | `frontend/src/components/LlmStatusBadge.tsx` |
| **5. UptimeRobot (optional)** | External keep-alive pinging `/api/warmup` every 5 min. Works with any plan. See below. | External service |

### Optional: Vercel Cron (requires Pro plan)

If you're on Vercel Pro, you can add a serverless function that pings the backend every 5 min to keep it warm between judge visits. Add this to `frontend/vercel.json`:

```json
"crons": [
  { "path": "/api/warmup-cron", "schedule": "*/5 * * * *" }
]
```

And create `frontend/api/warmup-cron.ts` that fetches `${BACKEND_URL}/api/warmup`. **Note:** Vercel Hobby plan only allows daily cron frequency — you need Pro for `*/5 * * * *`.

### Alternative: UptimeRobot (free, works on any plan)

Set up a free [UptimeRobot](https://uptimerobot.com) monitor:

1. Create a free account
2. Add a new monitor → **HTTP(s)** type
3. URL: `https://decision-lens-apac.onrender.com/api/warmup`
4. Monitoring interval: **5 minutes**
5. Save

This gives you a second independent keep-alive + email alerts if the backend goes down.

### Environment Variables

For the Vercel cron function to ping your backend, set this in your Vercel project settings:

```
BACKEND_URL=https://decision-lens-apac.onrender.com
```

(Default is already set to this URL in `api/warmup-cron.ts` if you forget.)

