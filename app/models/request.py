from pydantic import BaseModel, Field
from typing import Optional, List, Any
from app.utils.enums import (
    LanguageEnum,
    ChannelEnum,
    UserTypeEnum,
    TransactionTypeEnum,
    TransactionStatusEnum,
)


class TransactionEntry(BaseModel):
    transaction_id: str
    timestamp: str
    type: Optional[TransactionTypeEnum] = None
    amount: Optional[float] = None
    counterparty: Optional[str] = None
    status: Optional[TransactionStatusEnum] = None


class TicketRequest(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier")
    complaint: str = Field(..., description="Customer complaint text")
    language: Optional[LanguageEnum] = Field(None, description="en, bn, or mixed")
    channel: Optional[ChannelEnum] = Field(None, description="Submission channel")
    user_type: Optional[UserTypeEnum] = Field(None, description="Type of user")
    campaign_context: Optional[str] = Field(None, description="Active campaign identifier")
    transaction_history: Optional[List[TransactionEntry]] = Field(
        default_factory=list, description="Recent transactions (2–5 entries)"
    )
    metadata: Optional[Any] = Field(None, description="Additional context from harness")
