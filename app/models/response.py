from pydantic import BaseModel, Field
from typing import Optional, List
from app.utils.enums import (
    EvidenceVerdictEnum,
    CaseTypeEnum,
    SeverityEnum,
    DepartmentEnum,
)


class TicketResponse(BaseModel):
    ticket_id: str = Field(..., description="Echoed ticket ID from request")
    relevant_transaction_id: Optional[str] = Field(
        None, description="Matched transaction ID or null"
    )
    evidence_verdict: EvidenceVerdictEnum = Field(
        ..., description="consistent | inconsistent | insufficient_data"
    )
    case_type: CaseTypeEnum = Field(..., description="Classified type of issue")
    severity: SeverityEnum = Field(..., description="low | medium | high | critical")
    department: DepartmentEnum = Field(..., description="Routing department")
    agent_summary: str = Field(..., description="1–2 sentence summary for support agent")
    recommended_next_action: str = Field(..., description="Suggested next step for agent")
    customer_reply: str = Field(..., description="Safe, professional customer-facing reply")
    human_review_required: bool = Field(..., description="True when human review is needed")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence 0–1")
    reason_codes: Optional[List[str]] = Field(None, description="Short reason labels")


class HealthResponse(BaseModel):
    status: str = "ok"
