from typing import Optional
from app.utils.enums import CaseTypeEnum, SeverityEnum, EvidenceVerdictEnum


def determine_severity(
    case_type: str,
    evidence_verdict: str,
    amount: Optional[float] = None,
) -> SeverityEnum:
    """
    Deterministic severity mapping per spec + sample case calibration.
    These rules override whatever Gemini may suggest.
    """
    if case_type == CaseTypeEnum.phishing_or_social_engineering:
        return SeverityEnum.critical

    if case_type == CaseTypeEnum.wrong_transfer:
        # Inconsistent evidence (established recipient) → medium, else high
        if evidence_verdict == EvidenceVerdictEnum.inconsistent:
            return SeverityEnum.medium
        return SeverityEnum.high

    if case_type == CaseTypeEnum.payment_failed:
        return SeverityEnum.high

    if case_type == CaseTypeEnum.duplicate_payment:
        return SeverityEnum.high

    if case_type == CaseTypeEnum.agent_cash_in_issue:
        return SeverityEnum.high

    if case_type == CaseTypeEnum.merchant_settlement_delay:
        return SeverityEnum.medium

    if case_type == CaseTypeEnum.refund_request:
        if evidence_verdict == EvidenceVerdictEnum.inconsistent:
            return SeverityEnum.medium
        return SeverityEnum.low

    # other / vague
    return SeverityEnum.low
