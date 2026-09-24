from backend.parsing.regex_patterns import parse_bank_email
from backend.core.money import format_inr


def test_hdfc_debit_is_normalized():
    item = parse_bank_email("Rs.450.00 debited from A/c XX1234 on 15-04-25 to VPA grocery@ybl (UPI/412839).", "HDFC", "mail-1")
    assert item["amount"] == -450
    assert item["bank"] == "hdfc"
    assert item["merchant"] == "VPA GROCERY"
    assert item["date"] == "2025-04-15"


def test_indian_currency_format():
    assert format_inr(123456.78) == "₹1,23,456.78"
    assert format_inr(-50, 0) == "−₹50"
