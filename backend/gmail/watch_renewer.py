"""Watch renewal policy kept separate from API request handling."""
def should_renew(expires_at_ms: int, now_ms: int) -> bool:
    """Renew a Gmail watch during its final 24 hours."""
    return expires_at_ms - now_ms < 24 * 60 * 60 * 1000
