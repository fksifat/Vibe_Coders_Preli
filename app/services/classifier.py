import os
import json
import logging
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from app.utils.helpers import parse_json_safe, normalize_text
from app.services.complaint_parser import (
    PHISHING_KEYWORDS, WRONG_TRANSFER_KEYWORDS, PAYMENT_FAILED_KEYWORDS,
    REFUND_KEYWORDS, DUPLICATE_KEYWORDS, SETTLEMENT_KEYWORDS, CASH_IN_KEYWORDS,
)
from app.utils.enums import CaseTypeEnum

logger = logging.getLogger(__name__)

# ── Gemini setup ───────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "investigator_prompt.txt"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")

# ── Valid enum sets ─────────────────────────────────────────────────────────────
_VALID_CASE_TYPES = {e.value for e in CaseTypeEnum}


# ── Rule-based fallback ────────────────────────────────────────────────────────
def _rule_based_classify(complaint: str, hints: dict, language: str) -> dict:
    lower = normalize_text(complaint)

    if hints.get("is_phishing"):
        return {
            "case_type": "phishing_or_social_engineering",
            "agent_summary": (
                "Customer reports a suspicious contact attempting to obtain sensitive "
                "account credentials. Immediate fraud team review required."
            ),
            "recommended_next_action": (
                "Escalate to fraud_risk team immediately. Confirm to customer that "
                "the company never asks for OTP or PIN. Log the reported contact."
            ),
            "customer_reply": (
                "Thank you for reaching out before sharing any information. "
                "We never ask for your PIN, OTP, or password under any circumstances. "
                "Please do not share these with anyone, even if they claim to be from us. "
                "Our fraud team has been notified."
            ) if language != "bn" else (
                "আপনার তথ্য শেয়ার না করে যোগাযোগ করার জন্য ধন্যবাদ। "
                "আমরা কখনো আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। "
                "আমাদের ফ্রড টিমকে জানানো হয়েছে।"
            ),
        }

    if hints.get("is_duplicate"):
        return {
            "case_type": "duplicate_payment",
            "agent_summary": "Customer reports a duplicate charge. Transaction history shows two identical payments in quick succession.",
            "recommended_next_action": "Verify with payments_ops. If biller confirms single receipt, initiate reversal of the duplicate transaction.",
            "customer_reply": "We have noted the possible duplicate payment. Our payments team will verify and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone.",
        }

    if hints.get("is_wrong_transfer"):
        return {
            "case_type": "wrong_transfer",
            "agent_summary": "Customer reports sending money to an unintended recipient. Multiple transactions may match — clarification needed.",
            "recommended_next_action": "Reply to customer asking for the recipient's number or transaction details to identify the correct transaction. Do not initiate dispute until transaction is confirmed.",
            "customer_reply": "Thank you for reaching out. We see multiple transactions that could match. Could you share the recipient's number or any other detail to help us identify the right transaction? Please do not share your PIN or OTP with anyone.",
        }

    if hints.get("is_payment_failed"):
        return {
            "case_type": "payment_failed",
            "agent_summary": "Customer reports a failed transaction with a possible balance deduction.",
            "recommended_next_action": "Investigate the transaction ledger status. If balance was deducted on a failed payment, initiate the automatic reversal flow.",
            "customer_reply": "We have noted the transaction issue. Our payments team will investigate and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone.",
        }

    if hints.get("is_settlement"):
        return {
            "case_type": "merchant_settlement_delay",
            "agent_summary": "Merchant reports a settlement that has not been received within the expected window.",
            "recommended_next_action": "Route to merchant_operations to verify settlement batch status and communicate a revised ETA.",
            "customer_reply": "We have noted your settlement concern. Our merchant operations team will check the batch status and update you through official channels.",
        }

    if hints.get("is_cash_in"):
        return {
            "case_type": "agent_cash_in_issue",
            "agent_summary": "Customer reports a cash-in via agent not reflected in their balance.",
            "recommended_next_action": "Investigate the cash-in transaction status with agent operations. Confirm settlement state and resolve within standard SLA.",
            "customer_reply": "আপনার ক্যাশ ইনের বিষয়ে আমরা অবগত হয়েছি। আমাদের এজেন্ট অপারেশন্স দল শীঘ্রই যাচাই করবে। অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না।"
            if language == "bn" else
            "We have noted your cash-in concern. Our agent operations team will verify and resolve this shortly. Please do not share your PIN or OTP with anyone.",
        }

    if hints.get("is_refund"):
        return {
            "case_type": "refund_request",
            "agent_summary": "Customer is requesting a refund for a recent transaction.",
            "recommended_next_action": "Inform customer that refund eligibility depends on transaction type and merchant policy.",
            "customer_reply": "Thank you for reaching out. Refund eligibility depends on the transaction type and applicable policy. Our team will review your request. Please do not share your PIN or OTP with anyone.",
        }

    return {
        "case_type": "other",
        "agent_summary": "Customer has raised a general support inquiry that requires review.",
        "recommended_next_action": "Reply to customer asking for specific details: transaction ID, amount, and description of the issue.",
        "customer_reply": "Thank you for reaching out. To help you faster, please share the transaction ID, the amount involved, and what went wrong. Please do not share your PIN or OTP with anyone.",
    }


async def classify(
    complaint: str,
    hints: dict,
    transaction_history: list,
    relevant_transaction_id: Optional[str],
    evidence_verdict: str,
    language: str,
    channel: Optional[str],
    user_type: Optional[str],
    campaign_context: Optional[str],
    ticket_id: str,
) -> dict:
    """
    Primary: Gemini with full context.
    Fallback: rule-based classifier.
    Returns dict with: case_type, agent_summary, recommended_next_action, customer_reply.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — using rule-based fallback.")
        return _rule_based_classify(complaint, hints, language)

    txn_json = json.dumps(
        [t.model_dump() if hasattr(t, "model_dump") else t for t in transaction_history],
        indent=2, default=str
    )

    prompt = _PROMPT_TEMPLATE.format(
        ticket_id=ticket_id,
        complaint=complaint,
        language=language,
        channel=channel or "unknown",
        user_type=user_type or "unknown",
        campaign_context=campaign_context or "none",
        transaction_history_json=txn_json if txn_json != "[]" else "No transaction history provided.",
        relevant_transaction_id=relevant_transaction_id or "null",
        evidence_verdict=evidence_verdict,
    )

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.15,
                max_output_tokens=1024,
            ),
        )
        raw = response.text
        logger.debug("Gemini raw: %.500s", raw)

        parsed = parse_json_safe(raw)
        if parsed is None:
            logger.warning("Failed to parse Gemini response — fallback.")
            return _rule_based_classify(complaint, hints, language)

        # Validate case_type
        case_type = parsed.get("case_type", "other")
        if case_type not in _VALID_CASE_TYPES:
            logger.warning("Invalid case_type from Gemini: %s — fallback.", case_type)
            parsed["case_type"] = _rule_based_classify(complaint, hints, language)["case_type"]

        # Ensure all required fields exist
        for field in ("agent_summary", "recommended_next_action", "customer_reply"):
            if not parsed.get(field):
                fallback = _rule_based_classify(complaint, hints, language)
                parsed[field] = fallback[field]

        return parsed

    except Exception as exc:
        logger.error("Gemini API error: %s — rule-based fallback.", exc)
        return _rule_based_classify(complaint, hints, language)
