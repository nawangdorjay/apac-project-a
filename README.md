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
    Calculates an objective, deterministic score (0–100) combining Data Quality, Trend Metrics, and Risk Ratios, blended with a capped (15% max weight) Gemini-derived opportunity index to prevent AI bias.
3.  **🎛️ "What-If" Scenario Simulator:** 
    Interact with sliders to test perturbations (e.g. increase public transit ridership by 30%), recompute the scoring formula instantly on CPU/GPU, and receive real-time, plain-language impacts narrated by the LLM.
4.  **🛡️ 4-Tier Redundant LLM Failover System:** 
    Bulletproof routing engine that guarantees API uptime during high traffic or quota exhaustions:
    $$\text{Gemini API (Cloud)} \longrightarrow \text{NVIDIA NIM (Cloud)} \longrightarrow \text{Ollama (Local/Network)} \longrightarrow \text{Mock Templates (Local)}$$
5.  **🖨️ PDF Executive Report Generator:** 
    Export clean, print-ready ReportLab-generated PDF files detailing analysis summaries, scorecards, and simulator deltas.
6.  **⚡ NVIDIA cuDF Acceleration:** 
    Integrates zero-code-change GPU acceleration. Uses RAPIDS `cudf.pandas` if hosted on a CUDA-supported environment, failing back seamlessly to CPU pandas.

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

*   **Frontend:** Vite, React, TypeScript, Tailwind CSS, Recharts, Zustand.
*   **Backend:** FastAPI, Pandas, NumPy, OpenPyXL, ReportLab, Google GenAI SDK.
*   **Hosting:** Vercel (Frontend), Render (Backend / Dockerized).

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

Render's free tier sleeps containers after ~15 min of inactivity. The first request after sleep takes 30–60s while uvicorn boots. We mitigate this with **three layers**:

| Layer | What it does | Where |
|-------|--------------|-------|
| **1. Vercel Cron** | Every 5 min, a Vercel Serverless Function pings `/api/warmup` to keep the container awake. | `frontend/api/warmup-cron.ts` + `frontend/vercel.json` `crons` |
| **2. Frontend warmup** | On Landing page mount, the client fires a background `GET /api/warmup` so the backend is booted before the user clicks anything. | `frontend/src/lib/api.ts` `warmupBackend()` + `Landing.tsx` |
| **3. Cold-start aware client** | All API calls go through `coldStartRequest()` which uses a 90s timeout on first call, retries once on network/timeout error, and surfaces state via `BackendWarmth` listeners. | `frontend/src/lib/api.ts` |
| **4. ColdStartLoader banner** | When warmth is `warming` or `cold`, a dismissible banner appears at the top: "Waking up the backend — first request after inactivity takes ~30–60s on Render free tier". | `frontend/src/components/ColdStartLoader.tsx` |
| **5. LLM badge cold-start state** | The `LlmStatusBadge` turns amber and pulses when the backend is cold-starting, so judges see we're aware of it. | `frontend/src/components/LlmStatusBadge.tsx` |

### Alternative: UptimeRobot

If Vercel Cron isn't enough (e.g. Vercel itself has cron reliability issues), set up a free [UptimeRobot](https://uptimerobot.com) monitor:

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

