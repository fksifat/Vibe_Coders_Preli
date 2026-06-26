import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.request import TicketRequest
from app.models.response import TicketResponse, HealthResponse
from app.services.response_generator import process_ticket

logger = logging.getLogger(__name__)

router = APIRouter()





@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["Health"],
)
async def health():
    """Return service health status. Must respond within 60 s of start."""
    return HealthResponse()


@router.post(
    "/analyze-ticket",
    response_model=TicketResponse,
    summary="Investigate and classify a CRM support ticket",
    tags=["Tickets"],
    responses={
        200: {"description": "Successful analysis"},
        400: {"description": "Malformed input or missing required fields"},
        422: {"description": "Schema valid but semantically invalid (e.g., empty complaint)"},
        500: {"description": "Internal server error"},
    },
)
async def analyze_ticket(ticket: TicketRequest):
    """
    Accept one customer support ticket with optional transaction history.
    Returns structured classification with evidence reasoning, routing,
    severity, and a safe customer reply.
    """
    logger.info(
        "Received ticket_id=%s  channel=%s  lang=%s  txns=%d",
        ticket.ticket_id,
        ticket.channel,
        ticket.language,
        len(ticket.transaction_history or []),
    )
    return await process_ticket(ticket)
