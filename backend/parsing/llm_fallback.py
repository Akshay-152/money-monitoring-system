"""Optional LLM parser boundary, disabled by default to protect email privacy."""
def parse_with_llm(body: str, provider: str = ""):
    """Return no result until an explicit provider adapter is configured."""
    raise RuntimeError("LLM fallback is disabled; add a reviewed provider adapter before enabling it")
