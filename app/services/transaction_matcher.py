import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from app.models.request import TransactionEntry

logger = logging.getLogger(__name__)


def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def match_transaction(
    transactions: List[TransactionEntry],
    hints: dict,
) -> Tuple[Optional[str], List[str]]:
    """
    Returns (matched_transaction_id or None, reason_codes list).

    Strategy (calibrated against all 10 sample cases):
    1. Duplicate detection: same amount + counterparty within 120s → pick 2nd (SAMPLE-10)
    2. Filter by extracted amount
    3. Narrow by time hint (today / yesterday)
    4. Narrow by transaction type keyword
    5. Exactly 1 → return it
    6. Multiple or zero → return None (insufficient_data)
    """
    if not transactions:
        return None, []

    now = datetime.now(timezone.utc)

    # ── 1. Duplicate detection ─────────────────────────────────────────────────
    for i in range(len(transactions)):
        for j in range(i + 1, len(transactions)):
            a, b = transactions[i], transactions[j]
            if a.amount == b.amount and a.counterparty == b.counterparty:
                ta, tb = _parse_ts(a.timestamp), _parse_ts(b.timestamp)
                if ta and tb and abs((tb - ta).total_seconds()) <= 120:
                    logger.info("Duplicate detected: %s vs %s", a.transaction_id, b.transaction_id)
                    # Return the second (later) transaction as the suspected duplicate
                    later = b if tb >= ta else a
                    return later.transaction_id, ["duplicate_detected"]

    # ── 2. Filter by amount ────────────────────────────────────────────────────
    amount = hints.get("amount")
    candidates = list(transactions)

    if amount is not None:
        amt_matches = [t for t in transactions if t.amount == amount]
        if amt_matches:
            candidates = amt_matches

    # ── 3. Narrow by time hint ─────────────────────────────────────────────────
    time_hint = hints.get("time_hint")
    if time_hint is not None and len(candidates) > 1:
        def in_window(t: TransactionEntry) -> bool:
            ts = _parse_ts(t.timestamp)
            if ts is None:
                return True
            age_h = (now - ts).total_seconds() / 3600
            if time_hint == 0:   # today → within last 36 h (lenient)
                return age_h <= 36
            if time_hint == 1:   # yesterday → 24–72 h ago
                return 24 <= age_h <= 72
            return True

        filtered = [t for t in candidates if in_window(t)]
        if filtered:
            candidates = filtered

    # ── 4. Narrow by transaction type ──────────────────────────────────────────
    if len(candidates) > 1:
        type_map = {
            "is_cash_in": ["cash_in"],
            "is_settlement": ["settlement"],
            "is_payment_failed": ["payment", "transfer"],
            "is_wrong_transfer": ["transfer"],
        }
        for hint_key, type_values in type_map.items():
            if hints.get(hint_key):
                tf = [t for t in candidates if t.type and t.type.value in type_values]
                if tf:
                    candidates = tf
                    break

    # ── 5. Exactly 1 candidate ────────────────────────────────────────────────
    if len(candidates) == 1:
        return candidates[0].transaction_id, ["single_match"]

    # ── 6. Still multiple → ambiguous; return None ────────────────────────────
    if len(candidates) > 1:
        logger.info("Ambiguous match: %d candidates", len(candidates))
        return None, ["ambiguous_match"]

    # ── 7. Zero candidates after filtering → try bare amount match ────────────
    if amount is not None:
        bare = [t for t in transactions if t.amount == amount]
        if len(bare) == 1:
            return bare[0].transaction_id, ["amount_match_fallback"]

    return None, []
