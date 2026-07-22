# Try loading NVIDIA RAPIDS cuDF pandas accelerator (zero-code-change GPU acceleration)
try:
    import cudf.pandas
    cudf.pandas.install()
    print("[RAPIDS] NVIDIA cuDF pandas accelerator successfully loaded!")
    RAPIDS_ACTIVE = True
except ImportError:
    print("[RAPIDS] cuDF not available, falling back to standard CPU pandas.")
    RAPIDS_ACTIVE = False

import os
import uuid
import time
import io
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from dotenv import load_dotenv

from models.schemas import (
    UploadResponse, DecisionScoreResponse, WhatIfRequest, WhatIfResponse,
    ChatRequest, ChatResponse, SubScores, Priority, Recommendation, ScoreSnapshot,
    ForecastResponse, AutomationRequest, AutomationResponse
)
from services.cleaner import clean_dataframe
from services.profiler import profile_dataframe
from services.scorer import compute_decision_score, perturb_and_rescore, forecast_series
from services.gemini_client import (
    generate_summary, generate_opportunity_score,
    generate_recommendations, generate_whatif_explanation, generate_chat_response
)
from services.pdf_generator import generate_pdf_report

load_dotenv()

app = FastAPI(
    title="DecisionLens AI API",
    description="From Data to Decisions in Seconds",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (for hackathon; replace with Redis/DB for production)
sessions: Dict[str, Dict[str, Any]] = {}

DEMO_DATA_DIR = Path(__file__).parent / "demo_data"


def load_demo_data(dataset_name: str) -> pd.DataFrame:
    """Load a pre-baked demo CSV."""
    path = DEMO_DATA_DIR / f"{dataset_name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Demo dataset '{dataset_name}' not found")
    return pd.read_csv(path)


@app.get("/")
def root():
    return {"message": "DecisionLens AI API is running", "version": "1.0.0", "rapids_active": RAPIDS_ACTIVE}


@app.get("/health")
def health():
    return {"status": "healthy", "rapids_active": RAPIDS_ACTIVE}


# ── UPLOAD ────────────────────────────────────────────────────────────────────

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: Optional[UploadFile] = File(None),
    dataset_context: str = Form("business"),
    demo_dataset: Optional[str] = Form(None)
):
    """
    Upload a CSV/XLSX file or select a demo dataset.
    Returns session_id, cleaning_log, and preview rows.
    """
    start_time = int(time.time() * 1000)
    session_id = str(uuid.uuid4())

    try:
        if demo_dataset:
            # Load pre-baked demo dataset
            df = load_demo_data(demo_dataset)
            filename = f"{demo_dataset}.csv"
        elif file:
            content = await file.read()
            filename = file.filename or "upload.csv"
            if filename.endswith(".xlsx") or filename.endswith(".xls"):
                df = pd.read_excel(io.BytesIO(content))
            else:
                df = pd.read_csv(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="No file or demo dataset provided")

        rows_before = len(df)
        df_clean, cleaning_log = clean_dataframe(df)
        rows_after = len(df_clean)

        preview_rows = df_clean.head(5).fillna("").to_dict(orient="records")
        # Convert any numpy types to Python native
        preview_rows = json.loads(json.dumps(preview_rows, default=str))

        sessions[session_id] = {
            "df": df_clean,
            "filename": filename,
            "dataset_context": dataset_context,
            "cleaning_log": cleaning_log,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "start_time_ms": start_time,
            "profile_data": None,
            "summary_data": None,
            "score_data": None,
            "whatif_data": None,
        }

        return UploadResponse(
            session_id=session_id,
            filename=filename,
            dataset_context=dataset_context,
            cleaning_log=cleaning_log,
            rows_before=rows_before,
            rows_after=rows_after,
            preview_rows=preview_rows,
            rapids_active=RAPIDS_ACTIVE
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ── DATA (full cleaned rows for charts) ───────────────────────────────────────

@app.get("/api/data/{session_id}")
def get_session_data(session_id: str, limit: int = 500):
    """
    Return the cleaned dataset rows (capped at `limit`) for client-side charting.
    The 5-row preview returned by /api/upload is insufficient for dashboards.
    """
    session = _get_session(session_id)
    df = session["df"]

    limit = max(1, min(int(limit), 2000))  # hard cap at 2000 rows
    rows = df.head(limit).fillna("").to_dict(orient="records")
    rows = json.loads(json.dumps(rows, default=str))

    return JSONResponse({
        "session_id": session_id,
        "rows": rows,
        "total_rows": len(df),
        "returned_rows": len(rows),
        "columns": list(df.columns),
    })


# ── PROFILE ───────────────────────────────────────────────────────────────────

@app.get("/api/profile/{session_id}")
def get_profile(session_id: str):
    """
    Run pandas profiling on the uploaded dataset.
    100% deterministic — no AI calls.
    """
    session = _get_session(session_id)
    df = session["df"]

    profile = profile_dataframe(df)
    profile["session_id"] = session_id
    sessions[session_id]["profile_data"] = profile

    return profile


# ── SUMMARY ───────────────────────────────────────────────────────────────────

@app.post("/api/summary/{session_id}")
def get_summary(session_id: str):
    """
    Call Gemini to generate an AI narrative summary + key findings.
    """
    session = _get_session(session_id)
    profile = session.get("profile_data")
    if not profile:
        raise HTTPException(status_code=400, detail="Run /api/profile first")

    dataset_context = session.get("dataset_context", "business")
    summary = generate_summary(profile, dataset_context)
    sessions[session_id]["summary_data"] = summary

    summary["session_id"] = session_id
    return summary


# ── DECISION SCORE ────────────────────────────────────────────────────────────

@app.post("/api/decision-score/{session_id}")
def get_decision_score(session_id: str):
    """
    Compute Decision Score: 3 deterministic sub-scores + 1 Gemini opportunity sub-score.
    Also returns top priorities, recommendations, and time_to_insight_ms.
    """
    session = _get_session(session_id)
    df = session["df"]
    profile = session.get("profile_data")
    summary = session.get("summary_data")

    if not profile:
        raise HTTPException(status_code=400, detail="Run /api/profile first")

    dataset_context = session.get("dataset_context", "business")
    key_findings = summary.get("key_findings", []) if summary else []

    # Get Gemini opportunity sub-score
    opportunity_score = generate_opportunity_score(profile, dataset_context)

    # Compute full Decision Score (deterministic formula + opportunity)
    score_result = compute_decision_score(df, profile, opportunity_score)

    # Get recommendations from Gemini
    recs = generate_recommendations(score_result["sub_scores"], key_findings, dataset_context)

    # Compute Time to Insight
    start_time = session.get("start_time_ms", int(time.time() * 1000))
    time_to_insight_ms = int(time.time() * 1000) - start_time

    score_data = {
        **score_result,
        "top_priorities": recs.get("top_priorities", []),
        "recommendations": recs.get("recommendations", []),
        "time_to_insight_ms": time_to_insight_ms,
        "session_id": session_id,
        "rapids_active": RAPIDS_ACTIVE
    }

    sessions[session_id]["score_data"] = score_data
    sessions[session_id]["time_to_insight_ms"] = time_to_insight_ms

    return score_data


# ── WHAT-IF SIMULATOR ─────────────────────────────────────────────────────────

@app.post("/api/whatif/{session_id}")
def run_whatif(session_id: str, request: WhatIfRequest):
    """
    Scenario simulation (trend projection — NOT a forecast or prediction).
    Perturbs a column and re-runs the exact same deterministic Decision Score formula.
    One Gemini call for plain-language delta explanation.
    """
    session = _get_session(session_id)
    df = session["df"]
    profile = session.get("profile_data")
    score_data = session.get("score_data")

    if not profile or not score_data:
        raise HTTPException(status_code=400, detail="Run /api/profile and /api/decision-score first")

    if request.column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{request.column}' not found")

    # Get original opportunity score to keep consistent
    original_opportunity = score_data["sub_scores"]["opportunity"]

    # Perturb and rescore
    new_score_result = perturb_and_rescore(
        df, profile, request.column, request.pct_change, original_opportunity
    )

    old_snapshot = {
        "score": score_data["score"],
        "risk_level": score_data["risk_level"],
        "confidence": score_data["confidence"],
        "sub_scores": score_data["sub_scores"]
    }

    # One Gemini call for delta explanation
    dataset_context = session.get("dataset_context", "business")
    delta_explanation = generate_whatif_explanation(
        request.column, request.pct_change,
        old_snapshot, new_score_result, dataset_context
    )

    whatif_result = {
        "session_id": session_id,
        "column": request.column,
        "pct_change": request.pct_change,
        "old_score": old_snapshot,
        "new_score": new_score_result,
        "delta_explanation": delta_explanation,
        "scenario_deltas": new_score_result.get("scenario_deltas", {})
    }

    sessions[session_id]["whatif_data"] = whatif_result
    return whatif_result


# ── PDF REPORT ────────────────────────────────────────────────────────────────

@app.post("/api/report/{session_id}")
def generate_report(session_id: str):
    """
    Generate executive PDF report including what-if section if run.
    Returns PDF as binary.
    """
    session = _get_session(session_id)

    session_data = {
        "filename": session.get("filename", "Dataset"),
        "dataset_context": session.get("dataset_context", "business"),
        "cleaning_log": session.get("cleaning_log", []),
        "score_data": session.get("score_data", {}),
        "summary_data": session.get("summary_data", {}),
        "profile_data": session.get("profile_data", {}),
        "whatif_data": session.get("whatif_data"),
        "time_to_insight_ms": session.get("time_to_insight_ms"),
    }

    try:
        pdf_bytes = generate_pdf_report(session_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="DecisionLens_Report.pdf"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ── CHAT (P1) ─────────────────────────────────────────────────────────────────

@app.post("/api/chat/{session_id}")
def chat_with_dataset(session_id: str, request: ChatRequest):
    """
    P1 feature: Chat with dataset using Gemini + profile context.
    Never sends raw data to Gemini — only profiling stats.
    """
    session = _get_session(session_id)
    profile = session.get("profile_data")

    if not profile:
        raise HTTPException(status_code=400, detail="Run /api/profile first")

    dataset_context = session.get("dataset_context", "business")
    history = [{"role": m.role, "content": m.content} for m in request.history]

    result = generate_chat_response(request.message, history, profile, dataset_context)
    return result


# ── FORECASTING & WORKFLOWS ───────────────────────────────────────────────────

@app.get("/api/forecast/{session_id}", response_model=ForecastResponse)
def get_forecast(session_id: str, column: str, periods: int = 3):
    """
    Linear trend projection (least-squares fit) on a numeric column.
    Returns historical points + projected points with 95% CI bands.

    NOTE: This is a naive extrapolation, not an ML forecast. It assumes
    the historical linear trend continues unchanged. The What-If simulator
    uses 'scenario simulation' framing for perturbation deltas — this
    endpoint is for sanity-checking momentum only.
    """
    session = _get_session(session_id)
    df = session["df"]

    result = forecast_series(df, column, periods)
    if not result["historical"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return ForecastResponse(
        column=column,
        historical=result["historical"],
        projected=result["projected"],
        message=result["message"]
    )


@app.post("/api/automate/{session_id}", response_model=AutomationResponse)
def run_automation(session_id: str, request: AutomationRequest):
    """
    Simulated workflow automation.
    Triggers an intelligent action (log ticket / dispatch alert) based on recommendations.
    """
    session = _get_session(session_id)
    from datetime import datetime
    
    timestamp = datetime.now().isoformat()
    action_text = request.recommendation_text
    
    # Simulate routing logic based on recommendation content
    if "quality" in action_text.lower() or "missing" in action_text.lower():
        status = "Completed"
        message = "Data cleaning pipeline task logged."
        details = {
            "workflow_type": "Data Governance Ticket",
            "action_taken": "Assigned data validation task to Data Quality queue.",
            "integration": "Google Cloud Tasks"
        }
    elif "revenue" in action_text.lower() or "sales" in action_text.lower() or "cost" in action_text.lower():
        status = "Active"
        message = "Scheduled weekly digest rule."
        details = {
            "workflow_type": "Executive Digest Alert",
            "action_taken": "Configured custom trigger rule on Pub/Sub topic.",
            "integration": "Google Cloud Pub/Sub"
        }
    else:
        status = "Dispatched"
        message = "Alert dispatched successfully."
        details = {
            "workflow_type": "Citizen / Community Action Notification",
            "action_taken": f"Dispatched alert notification to smart-community channel. Payload: '{action_text}'",
            "integration": "Google Cloud Functions API"
        }
        
    return AutomationResponse(
        status=status,
        message=message,
        timestamp=timestamp,
        details=details
    )


# ── SESSION HELPER ────────────────────────────────────────────────────────────

def _get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found. Please upload a file first.")
    return sessions[session_id]


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # Generate demo data on startup
    from generate_demo_data import generate_demo_datasets
    generate_demo_datasets()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
