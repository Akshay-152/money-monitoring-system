"""Keyword and learning based transaction categorisation."""
MERCHANT_CATEGORIES = {
    "BIGBASKET": "Groceries", "GROFERS": "Groceries", "ZEPTO": "Groceries", "BLINKIT": "Groceries", "DMART": "Groceries",
    "SWIGGY": "Food", "ZOMATO": "Food", "DOMINOS": "Food", "MCDONALDS": "Food", "KFC": "Food", "STARBUCKS": "Food",
    "OLA": "Transport", "UBER": "Transport", "RAPIDO": "Transport", "IRCTC": "Transport", "FASTAG": "Transport", "PETROL": "Transport",
    "AMAZON": "Shopping", "FLIPKART": "Shopping", "MYNTRA": "Shopping", "AJIO": "Shopping", "NYKAA": "Shopping", "MEESHO": "Shopping",
    "AIRTEL": "Bills", "JIO": "Bills", "VODAFONE": "Bills", "BSNL": "Bills", "TATA POWER": "Bills", "BESCOM": "Bills",
    "NETFLIX": "Entertainment", "SPOTIFY": "Entertainment", "HOTSTAR": "Entertainment", "BOOKMYSHOW": "Entertainment", "PVR": "Entertainment",
    "PHARMEASY": "Health", "APOLLO": "Health", "1MG": "Health", "PRACTO": "Health", "GYM": "Health",
    "BYJU": "Education", "UNACADEMY": "Education", "COURSERA": "Education", "UDEMY": "Education",
    "MAKEMYTRIP": "Travel", "GOIBIBO": "Travel", "YATRA": "Travel", "IXIGO": "Travel", "AIRBNB": "Travel", "OYO": "Travel",
    "RENT": "Rent", "LANDLORD": "Rent", "NOBROKER": "Rent", "ZERODHA": "Investment", "GROWW": "Investment", "SIP": "Investment",
}
CATEGORIES = ["Rent", "Groceries", "Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Education", "Travel", "Investment", "Gift", "Other"]


def categorise(merchant: str, rules: dict[str, str] | None = None) -> str:
    """Suggest a category while keeping the decision visible for user confirmation."""
    key = merchant.upper()
    if rules and key in rules:
        return rules[key]
    for keyword, category in MERCHANT_CATEGORIES.items():
        if keyword in key:
            return category
    return ""
