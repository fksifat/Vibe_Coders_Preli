import re
from typing import Optional
from app.utils.helpers import normalize_text

# ── Amount extraction ─────────────────────────────────────────────────────────
_AMOUNT_PATTERNS = [
    r"(\d[\d,]*)\s*(?:taka|bdt|tk|৳|টাকা)",
    r"(?:taka|bdt|tk|৳|টাকা)\s*(\d[\d,]*)",
    r"(?:sent|paid|transfer|send|deducted|charged)\s+(\d[\d,]+)",
    r"(?:of|for)\s+(\d[\d,]+)\s+taka",
]

# ── Time hints (days_ago: 0=today, 1=yesterday) ────────────────────────────────
_TIME_HINTS = {
    "today": 0, "this morning": 0, "this afternoon": 0,
    "this evening": 0, "just now": 0, "few minutes": 0,
    "আজ": 0, "আজকে": 0, "সকালে": 0, "আজ সকালে": 0,
    "yesterday": 1, "last night": 1, "গতকাল": 1,
}

# ── Keyword signals ────────────────────────────────────────────────────────────
PHISHING_KEYWORDS = [
    "otp", "pin", "password", "verification code", "verify your account",
    "share your", "told me to share", "someone called", "called asking",
    "asked for my otp", "asked for my pin", "someone asked",
    "security code", "account will be blocked", "will be blocked if",
    "একটি কোড", "পিন", "ওটিপি", "পাসওয়ার্ড",
]
WRONG_TRANSFER_KEYWORDS = [
    "wrong number", "wrong account", "wrong recipient", "sent to wrong",
    "ভুল নম্বর", "wrong transfer", "mistakenly sent", "accidentally sent",
    "wrong person", "wrong bkash", "wrong mobile",
    "he didn't get it", "he says he didn't", "she didn't get",
    "didn't receive", "not received it", "brother didn't", "friend didn't",
    "sent but not", "not getting",
]
PAYMENT_FAILED_KEYWORDS = [
    "payment failed", "transaction failed", "balance deducted", "failed but",
    "money deducted", "deducted but", "showed failed", "app showed failed",
    "পেমেন্ট ফেল", "ব্যালেন্স কাটা",
]
REFUND_KEYWORDS = [
    "refund", "money back", "return my money", "cancel",
    "changed my mind", "want it back", "ফেরত", "রিফান্ড",
]
DUPLICATE_KEYWORDS = [
    "deducted twice", "charged twice", "double charge", "paid twice",
    "duplicate", "deducted two times", "দুইবার", "দুবার",
]
SETTLEMENT_KEYWORDS = [
    "settlement", "not settled", "settlement delay",
    "sales not settled", "settle", "সেটেলমেন্ট",
]
CASH_IN_KEYWORDS = [
    "cash in", "cash-in", "cashin", "ক্যাশ ইন",
    "agent cash", "deposited", "agent deposit", "ক্যাশইন",
]


def extract_amount(complaint: str) -> Optional[float]:
    for pattern in _AMOUNT_PATTERNS:
        m = re.search(pattern, complaint, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    # Fallback: largest standalone number (≥ 3 digits) in text
    numbers = re.findall(r"\b(\d{3,})\b", complaint)
    if numbers:
        try:
            return float(max(numbers, key=lambda x: int(x)))
        except ValueError:
            pass
    return None


def extract_time_hint(complaint: str) -> Optional[int]:
    lower = complaint.lower()
    for hint, days_ago in _TIME_HINTS.items():
        if hint in lower:
            return days_ago
    return None


def parse_complaint(complaint: str) -> dict:
    lower = normalize_text(complaint)
    return {
        "amount": extract_amount(complaint),
        "time_hint": extract_time_hint(complaint),
        "is_phishing": any(kw in lower for kw in PHISHING_KEYWORDS),
        "is_wrong_transfer": any(kw in lower for kw in WRONG_TRANSFER_KEYWORDS),
        "is_payment_failed": any(kw in lower for kw in PAYMENT_FAILED_KEYWORDS),
        "is_refund": any(kw in lower for kw in REFUND_KEYWORDS),
        "is_duplicate": any(kw in lower for kw in DUPLICATE_KEYWORDS),
        "is_settlement": any(kw in lower for kw in SETTLEMENT_KEYWORDS),
        "is_cash_in": any(kw in lower for kw in CASH_IN_KEYWORDS),
    }
