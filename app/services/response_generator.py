import logging
from app.models.request import TicketRequest
from app.models.response import TicketResponse
from app.utils.helpers import detect_language
from app.services.validator import validate_ticket
from app.services.complaint_parser import parse_complaint
from app.services.transaction_matcher import match_transaction
from app.services.evidence_engine import determine_evidence_verdict
from app.services.classifier import classify
from app.services.severity import determine_severity
from app.services.router import determine_department
from app.services.review_engine import determine_human_review
from app.services.safety import scrub_reply, scrub_next_action

logger = logging.getLogger(__name__)


async def process_ticket(ticket: TicketRequest) -> TicketResponse:
    """
    Main orchestrator. Runs the full investigator pipeline:
    1. Validate input
    2. Parse complaint → extract hints
    3. Match transaction → relevant_transaction_id
    4. Determine evidence_verdict
    5. Classify with Gemini (+ fallback) → case_type, summaries, reply
    6. Determine severity (rule-based override)
    7. Route department (rule-based)
    8. Determine human_review_required
    9. Scrub safety on outputs
    10. Assemble and return TicketResponse
    """
    # ── 1. Validate ────────────────────────────────────────────────────────────
    validate_ticket(ticket)

    # ── 2. Parse complaint ─────────────────────────────────────────────────────
    hints = parse_complaint(ticket.complaint)

    # Determine effective language
    language = (
        ticket.language.value
        if ticket.language
        else detect_language(ticket.complaint)
    )

    transactions = ticket.transaction_history or []

    # ── 3. Transaction matching ────────────────────────────────────────────────
    relevant_txn_id, reason_codes = match_transaction(transactions, hints)

    # ── 4. Evidence verdict ────────────────────────────────────────────────────
    evidence_verdict = determine_evidence_verdict(
        relevant_txn_id, transactions, hints, reason_codes
    )

    logger.info(
        "ticket_id=%s  txn=%s  verdict=%s  lang=%s",
        ticket.ticket_id, relevant_txn_id, evidence_verdict.value, language,
    )

    # ── 5. Classify (Gemini + fallback) ───────────────────────────────────────
    classification = await classify(
        complaint=ticket.complaint,
        hints=hints,
        transaction_history=transactions,
        relevant_transaction_id=relevant_txn_id,
        evidence_verdict=evidence_verdict.value,
        language=language,
        channel=ticket.channel.value if ticket.channel else None,
        user_type=ticket.user_type.value if ticket.user_type else None,
        campaign_context=ticket.campaign_context,
        ticket_id=ticket.ticket_id,
    )

    case_type = classification["case_type"]
    agent_summary = classification.get("agent_summary", "")
    recommended_next_action = classification.get("recommended_next_action", "")
    customer_reply = classification.get("customer_reply", "")
    confidence = float(classification.get("confidence", 0.80))
    confidence = max(0.0, min(1.0, confidence))

    # ── Rule-based case_type override (fix Gemini misclassifications) ──────────
    # Priority: phishing > duplicate > wrong_transfer > payment_failed > cash_in > settlement
    if hints.get("is_phishing") and case_type not in ("phishing_or_social_engineering",):
        case_type = "phishing_or_social_engineering"
    elif hints.get("is_duplicate") and case_type == "other":
        case_type = "duplicate_payment"
    elif hints.get("is_wrong_transfer") and case_type == "other":
        case_type = "wrong_transfer"
    elif hints.get("is_cash_in") and case_type == "other":
        case_type = "agent_cash_in_issue"
    elif hints.get("is_settlement") and case_type == "other":
        case_type = "merchant_settlement_delay"

    # ── 6. Severity (deterministic override) ──────────────────────────────────
    severity = determine_severity(case_type, evidence_verdict.value, hints.get("amount"))

    # ── 7. Department routing ──────────────────────────────────────────────────
    department = determine_department(case_type, severity.value, evidence_verdict.value)

    # ── 8. Human review decision ───────────────────────────────────────────────
    human_review = determine_human_review(
        case_type, severity.value, evidence_verdict.value, reason_codes
    )

    # ── 9. Safety scrub ────────────────────────────────────────────────────────
    customer_reply = scrub_reply(customer_reply, language)
    recommended_next_action = scrub_next_action(recommended_next_action)

    logger.info(
        "ticket_id=%s → case=%s  severity=%s  dept=%s  human=%s",
        ticket.ticket_id, case_type, severity.value, department.value, human_review,
    )

    # ── 10. Assemble response ──────────────────────────────────────────────────
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        relevant_transaction_id=relevant_txn_id,
        evidence_verdict=evidence_verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        agent_summary=agent_summary,
        recommended_next_action=recommended_next_action,
        customer_reply=customer_reply,
        human_review_required=human_review,
        confidence=confidence,
        reason_codes=reason_codes if reason_codes else None,
    )
