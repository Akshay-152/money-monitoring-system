"""Bank alert extraction using deterministic patterns before any LLM fallback."""
from datetime import datetime
import re
from .normaliser import normalise_merchant
from .categoriser import categorise

BANKS = ("hdfc", "icici", "sbi", "axis", "kotak", "yes", "idfc", "punjab")
AMOUNT = re.compile(r"(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.I)
DATE = re.compile(r"(\d{1,2}[-/]\w{3,9}[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", re.I)


def parse_bank_email(body: str, bank: str = "unknown", email_id: str = "") -> dict:
    """Parse common Indian bank alerts into the normalized transaction model."""
    amount_match = AMOUNT.search(body)
    if not amount_match:
        raise ValueError("No INR amount found")
    amount = float(amount_match.group(1).replace(",", ""))
    lowered = body.lower()
    direction = "credit" if any(word in lowered for word in ("credited", "received", "deposited")) and "debited" not in lowered else "debit"
    merchant_match = re.search(r"(?:to|at|towards|info:\s*)(?:UPI[/\s-]*)?([^.;]+)", body, re.I)
    merchant_raw = merchant_match.group(1).strip() if merchant_match else "Unknown UPI payment"
    merchant = normalise_merchant(merchant_raw)
    date_match = DATE.search(body)
    parsed_date = datetime.now().date().isoformat()
    if date_match:
        raw = date_match.group(1).replace("/", "-")
        for fmt in ("%d-%m-%Y", "%d-%m-%y", "%d-%b-%Y", "%d-%b-%y", "%d-%B-%Y", "%d-%B-%y"):
            try:
                parsed_date = datetime.strptime(raw.title(), fmt).date().isoformat()
                break
            except ValueError:
                continue
    return {"amount": amount if direction == "credit" else -amount, "currency": "INR", "merchant": merchant, "merchant_raw": merchant_raw, "category": categorise(merchant), "classified": False, "payment_mode": "UPI", "source": "gmail", "bank": bank.lower(), "email_message_id": email_id, "date": parsed_date, "ts": int(datetime.now().timestamp() * 1000), "deleted_at": None, "parse_failed": False, "notes": ""}
