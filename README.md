# 🏙️ DecisionLens AI

> **Decision Intelligence & Scenario Simulation Platform for Smart Communities**  
> Built for the *Google GenAI Academy APAC Hackathon* 🚀

[![Frontend Live](https://img.shields.io/badge/Frontend-Vercel%20Live-brightgreen?style=for-the-badge&logo=vercel)](https://frontend-iota-one-33.vercel.app)
[![API Docs](https://img.shields.io/badge/API%20Docs-Render%20Live-blue?style=for-the-badge&logo=fastapi)](https://decision-lens-apac.onrender.com/docs)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM%20Active-76B900?style=for-the-badge&logo=nvidia)](https://build.nvidia.com)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%20Active-8E75C2?style=for-the-badge&logo=google-gemini)](https://aistudio.google.com)

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
