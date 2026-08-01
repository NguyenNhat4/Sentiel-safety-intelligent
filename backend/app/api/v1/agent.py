from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.services.llm_service import SafetyAgentService

router = APIRouter(prefix="/agent", tags=["AI Safety Agent"])
agent_service = SafetyAgentService()


class AgentQueryRequest(BaseModel):
    message: str = Field(..., description="Query or prompt for the AI Safety Agent")
    context: dict[str, Any] | None = None


class AgentQueryResponse(BaseModel):
    response: str
    recommendation: str | None = None


@router.post("/chat", response_model=AgentQueryResponse)
async def chat_with_safety_agent(request: AgentQueryRequest):
    """Chat with Safety Officer AI Agent for incident analysis and rule advice."""
    ctx = request.context or {"event_type": "general", "zone_id": "all", "severity": "medium"}
    rec = agent_service.generate_recommendation(ctx)
    return AgentQueryResponse(
        response=f"Received query: '{request.message}'. AI Recommendation: {rec}",
        recommendation=rec,
    )
