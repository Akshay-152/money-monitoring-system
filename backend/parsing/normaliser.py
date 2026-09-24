"""Merchant cleanup shared by every parser."""
import re


def normalise_merchant(value: str) -> str:
    """Turn noisy UPI descriptors into stable uppercase merchant keys."""
    cleaned = value.upper().strip()
    cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"\s*@\w+", "", cleaned)
    cleaned = re.sub(r"[-_/]?(PAYMENT|UPI)$", "", cleaned)
    cleaned = re.sub(r"\s*[-_/]\d+$", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip() or "UNKNOWN UPI PAYMENT"
