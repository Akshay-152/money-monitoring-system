"""Indian Rupee formatting and numeric helpers."""
from decimal import Decimal, ROUND_HALF_UP


def format_inr(amount: float, decimals: int = 2) -> str:
    """Format INR with Indian lakh/crore grouping and a Unicode minus sign."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "−" if value < 0 else ""
    text = f"{abs(value):.{decimals}f}"
    whole, _, fraction = text.partition(".")
    last = whole[-3:]
    prefix = whole[:-3]
    if prefix:
        groups = []
        while prefix:
            groups.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        whole = ",".join(groups + [last])
    else:
        whole = last
    return f"{sign}₹{whole}" + (f".{fraction}" if decimals else "")


def compact_inr(amount: float) -> str:
    """Format large values compactly for dashboard statistics."""
    absolute = abs(amount)
    suffix = ""
    divisor = 1
    if absolute >= 10_000_000:
        suffix, divisor = "Cr", 10_000_000
    elif absolute >= 100_000:
        suffix, divisor = "L", 100_000
    if not suffix:
        return format_inr(amount, 0)
    sign = "−" if amount < 0 else ""
    return f"{sign}₹{absolute / divisor:.1f}{suffix}"
