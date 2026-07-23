from pydantic import BaseModel
from typing import Optional, List, Any, Dict

class ColumnProfile(BaseModel):
    name: str
    dtype: str
    nulls_pct: float
    unique_count: int
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    outlier_count: int = 0
    sample_values: List[Any] = []

class ProfilingResult(BaseModel):
    session_id: str
    row_count: int
    column_count: int
    columns: List[ColumnProfile]
    correlations: Dict[str, Dict[str, float]] = {}
    overall_quality_pct: float

class CleaningResult(BaseModel):
    session_id: str
    cleaning_log: List[str]
    rows_before: int
    rows_after: int
    preview_rows: List[Dict[str, Any]]

class UploadResponse(BaseModel):
    session_id: str
    filename: str
    dataset_context: str
    cleaning_log: List[str]
    rows_before: int
    rows_after: int
    preview_rows: List[Dict[str, Any]]
    rapids_active: bool = False

class SummaryResponse(BaseModel):
    session_id: str
    summary_text: str
    key_findings: List[str]

class SubScores(BaseModel):
    data_quality: float
    trend_stability: float
    risk_inverse: float
    opportunity: float

class Priority(BaseModel):
    text: str
    rationale: str
    impact_tag: str

class Recommendation(BaseModel):
    action: str
    rationale: str
    priority: str

class DecisionScoreResponse(BaseModel):
    session_id: str
    score: float
    risk_level: str
    confidence: float
    sub_scores: SubScores
    top_priorities: List[Priority]
    recommendations: List[Recommendation]
    time_to_insight_ms: Optional[int] = None
    rapids_active: bool = False

class WhatIfRequest(BaseModel):
    column: str
    pct_change: float

class WhatIfCompareRequest(BaseModel):
    scenario_a: WhatIfRequest
    scenario_b: WhatIfRequest

class ScoreSnapshot(BaseModel):
    score: float
    risk_level: str
    confidence: float
    sub_scores: SubScores

class WhatIfResponse(BaseModel):
    session_id: str
    column: str
    pct_change: float
    old_score: ScoreSnapshot
    new_score: ScoreSnapshot
    delta_explanation: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str
    referenced_columns: List[str] = []

class HistoricalPoint(BaseModel):
    index: int
    value: float

class ProjectedPoint(BaseModel):
    index: int
    value: float
    lower: float
    upper: float

class ForecastResponse(BaseModel):
    column: str
    historical: List[HistoricalPoint]
    projected: List[ProjectedPoint]
    message: str

class AutomationRequest(BaseModel):
    recommendation_text: str

class AutomationResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    details: Dict[str, Any]
