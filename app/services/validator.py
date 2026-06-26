from fastapi import HTTPException
from app.models.request import TicketRequest


def validate_ticket(ticket: TicketRequest) -> None:
    """Raise HTTPException for invalid inputs."""
    if not ticket.ticket_id or not ticket.ticket_id.strip():
        raise HTTPException(status_code=400, detail="Field 'ticket_id' is required and must not be empty.")
    if not ticket.complaint or not ticket.complaint.strip():
        raise HTTPException(status_code=422, detail="Field 'complaint' must not be empty.")
