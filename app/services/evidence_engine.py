from typing import Optional, List
from app.models.request import TransactionEntry
from app.utils.enums import EvidenceVerdictEnum


def determine_evidence_verdict(
    matched_txn_id: Optional[str],
    transactions: List[TransactionEntry],
    hints: dict,
    reason_codes: List[str],
) -> EvidenceVerdictEnum:
    """
    Determine evidence_verdict from matched transaction + complaint hints.

    Rules (calibrated against sample cases):
    - No match → insufficient_data
    - Duplicate explicitly detected → consistent
    - wrong_transfer claim but ≥2 prior transfers to same counterparty → inconsistent (SAMPLE-02)
    - Otherwise → consistent
    """
    if matched_txn_id is None:
        return EvidenceVerdictEnum.insufficient_data

    matched = next((t for t in transactions if t.transaction_id == matched_txn_id), None)
    if matched is None:
        return EvidenceVerdictEnum.insufficient_data

    # Duplicate already proven by detector
    if "duplicate_detected" in reason_codes:
        return EvidenceVerdictEnum.consistent

    # Inconsistency: wrong_transfer claim with established recipient pattern
    if hints.get("is_wrong_transfer") and matched.counterparty:
        prior_same = [
            t for t in transactions
            if t.counterparty == matched.counterparty
            and t.transaction_id != matched_txn_id
        ]
        if len(prior_same) >= 2:
            return EvidenceVerdictEnum.inconsistent

    return EvidenceVerdictEnum.consistent
