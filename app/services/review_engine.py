from typing import List
from app.utils.enums import CaseTypeEnum, SeverityEnum, EvidenceVerdictEnum


def determine_human_review(
    case_type: str,
    severity: str,
    evidence_verdict: str,
    reason_codes: List[str],
) -> bool:
    """
    Decide whether human_review_required = True.

    Calibrated against sample cases:
    - SAMPLE-01 (wrong_transfer, high, consistent) → True
    - SAMPLE-02 (wrong_transfer, medium, inconsistent) → True
    - SAMPLE-03 (payment_failed, high, consistent) → False (auto-reversible flow)
    - SAMPLE-04 (refund_request, low, consistent) → False
    - SAMPLE-05 (phishing, critical) → True
    - SAMPLE-06 (other, low, insufficient_data) → False
    - SAMPLE-07 (agent_cash_in_issue, high, consistent) → True
    - SAMPLE-08 (ambiguous match) → False (needs clarification first)
    - SAMPLE-09 (merchant_settlement_delay, medium) → False
    - SAMPLE-10 (duplicate_payment, high) → True
    """
    # Phishing always needs immediate human attention
    if case_type == CaseTypeEnum.phishing_or_social_engineering:
        return True

    # Ambiguous match → ask for clarification first, no human review yet
    if "ambiguous_match" in reason_codes:
        return False

    # Severity-based
    if severity == SeverityEnum.critical:
        return True
    if severity == SeverityEnum.high:
        # payment_failed is auto-reversible → no immediate human review
        if case_type == CaseTypeEnum.payment_failed:
            return False
        return True

    # Inconsistent evidence always needs human check
    if evidence_verdict == EvidenceVerdictEnum.inconsistent:
        return True

    # Dispute cases
    if case_type == CaseTypeEnum.wrong_transfer:
        return True
    if case_type == CaseTypeEnum.duplicate_payment:
        return True

    return False
