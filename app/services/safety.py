import re
import logging

logger = logging.getLogger(__name__)

# ── Patterns that indicate ASKING for credentials (violations) ─────────────────
# "do not share your PIN" is SAFE — we only flag the asking/requesting patterns.
_CREDENTIAL_PATTERNS = [
    re.compile(r"\bplease\s+share\s+your\s+(?:pin|otp|password)\b", re.I),
    re.compile(r"\bkindly\s+share\s+your\s+(?:pin|otp|password)\b", re.I),
    re.compile(r"\bprovide\s+(?:us\s+(?:with\s+)?)?your\s+(?:pin|otp|password)\b", re.I),
    re.compile(r"\benter\s+your\s+(?:pin|otp|password)\b", re.I),
    re.compile(r"\bsend\s+(?:us\s+)?your\s+(?:pin|otp|password)\b", re.I),
    re.compile(r"\bshare\s+your\s+(?:pin|otp|password)\b(?!\s+with\s+anyone)", re.I),
    re.compile(r"\bverify\s+(?:using\s+)?your\s+(?:pin|otp|password)\b", re.I),
    re.compile(r"\bconfirm\s+(?:with\s+)?your\s+(?:pin|otp|password)\b", re.I),
    re.compile(r"\byour\s+(?:4|6)[\s-]?digit\s+(?:pin|otp|code)\b", re.I),
    # Bangla credential request patterns
    re.compile(r"(?:পিন|ওটিপি|পাসওয়ার্ড)\s*(?:নম্বরটি|কোডটি)?\s*(?:প্রদান\s+করুন|দিন|শেয়ার\s+করুন|জানান|বলুন|পাঠান)", re.I),
    re.compile(r"(?:প্রদান\s+করুন|দিন|শেয়ার\s+করুন|জানান|বলুন|পাঠান)\s*(?:আপনার\s+)?(?:পিন|ওটিপি|পাসওয়ার্ড)", re.I),
]

# ── Unauthorized refund promise patterns ──────────────────────────────────────
_UNAUTHORIZED_REFUND_PATTERNS = [
    re.compile(r"\bwe\s+will\s+refund\s+you\b", re.I),
    re.compile(r"\byou\s+will\s+(?:get|receive)\s+(?:a\s+)?refund\b", re.I),
    re.compile(r"\bwe['']?ll\s+refund\b", re.I),
    re.compile(r"\brefund\s+(?:will\s+be|has\s+been)\s+(?:processed|initiated|sent)\b", re.I),
    re.compile(r"\byour\s+money\s+(?:will\s+be|has\s+been)\s+returned\b", re.I),
    re.compile(r"\bwe\s+(?:will|shall)\s+return\s+your\s+money\b", re.I),
]

_SAFE_REFUND_PHRASE = (
    "any eligible amount will be returned through official channels"
)

# ── Third-party redirect patterns ─────────────────────────────────────────────
_THIRD_PARTY_PATTERNS = [
    re.compile(r"\bcontact\s+(?:the\s+)?(?:police|cyber\s+crime|another\s+agent)\b", re.I),
    re.compile(r"\bvisit\s+(?:a\s+)?third[\s-]party\b", re.I),
]


def _check_credentials(text: str) -> bool:
    return any(p.search(text) for p in _CREDENTIAL_PATTERNS)


def _replace_unauthorized_refunds(text: str) -> str:
    for p in _UNAUTHORIZED_REFUND_PATTERNS:
        if p.search(text):
            logger.warning("Safety: unauthorized refund promise detected — replacing.")
            text = p.sub(_SAFE_REFUND_PHRASE, text)
    return text


def _check_third_party(text: str) -> bool:
    return any(p.search(text) for p in _THIRD_PARTY_PATTERNS)


# ── Credential safety footer by language ─────────────────────────────────────
_CREDENTIAL_REMINDER_EN = (
    " Please do not share your PIN or OTP with anyone."
)
_CREDENTIAL_REMINDER_BN = (
    " অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না।"
)


def scrub_reply(customer_reply: str, language: str = "en") -> str:
    """
    Scrub customer_reply for safety violations and ensure credential reminder.
    Returns a safe, compliant reply.
    """
    # Replace unauthorized refund promises
    reply = _replace_unauthorized_refunds(customer_reply)

    # If credential request or third-party redirect found → strip/replace and log warning
    if _check_credentials(reply) or _check_third_party(reply):
        logger.warning("Safety: violation (credential or third-party redirect) detected in customer_reply — replacing.")
        # Replace entire reply with a safe generic one
        if language == "bn":
            reply = (
                "আপনার সমস্যার বিষয়ে আমরা অবগত হয়েছি। আমাদের দল শীঘ্রই আপনার সাথে যোগাযোগ করবে।"
                + _CREDENTIAL_REMINDER_BN
            )
        else:
            reply = (
                "We have received your request and our team will review it shortly. "
                "Please contact us only through official support channels."
                + _CREDENTIAL_REMINDER_EN
            )
        return reply


    # Ensure credential safety reminder is present
    bn_reminder_present = "পিন" in reply and "ওটিপি" in reply
    en_reminder_present = (
        "pin" in reply.lower() and "otp" in reply.lower()
    ) or "do not share" in reply.lower()

    if language == "bn" and not bn_reminder_present:
        reply = reply.rstrip() + _CREDENTIAL_REMINDER_BN
    elif language != "bn" and not en_reminder_present:
        reply = reply.rstrip() + _CREDENTIAL_REMINDER_EN

    return reply


def scrub_next_action(next_action: str) -> str:
    """
    Scrub recommended_next_action for unauthorized refund language.
    """
    return _replace_unauthorized_refunds(next_action)
