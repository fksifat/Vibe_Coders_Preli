from app.utils.enums import CaseTypeEnum, DepartmentEnum, SeverityEnum, EvidenceVerdictEnum


def determine_department(
    case_type: str,
    severity: str,
    evidence_verdict: str,
) -> DepartmentEnum:
    """
    Deterministic department routing per spec taxonomy.
    """
    if case_type == CaseTypeEnum.phishing_or_social_engineering:
        return DepartmentEnum.fraud_risk

    if case_type == CaseTypeEnum.wrong_transfer:
        return DepartmentEnum.dispute_resolution

    if case_type in (CaseTypeEnum.payment_failed, CaseTypeEnum.duplicate_payment):
        return DepartmentEnum.payments_ops

    if case_type == CaseTypeEnum.merchant_settlement_delay:
        return DepartmentEnum.merchant_operations

    if case_type == CaseTypeEnum.agent_cash_in_issue:
        return DepartmentEnum.agent_operations

    if case_type == CaseTypeEnum.refund_request:
        # Contested refund (inconsistent evidence or medium severity) → dispute
        if evidence_verdict == EvidenceVerdictEnum.inconsistent or severity == SeverityEnum.medium:
            return DepartmentEnum.dispute_resolution
        return DepartmentEnum.customer_support

    # other
    return DepartmentEnum.customer_support
