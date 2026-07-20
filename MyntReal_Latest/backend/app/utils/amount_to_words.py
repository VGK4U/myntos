"""
Amount to Words Utility for Indian Rupees
Converts numeric amounts to words in Indian numbering system (Lakhs, Crores)
"""

from decimal import Decimal, ROUND_HALF_UP

ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
        'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
        'Seventeen', 'Eighteen', 'Nineteen']

TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _two_digits_to_words(num: int) -> str:
    if num < 20:
        return ONES[num]
    elif num < 100:
        tens = num // 10
        ones = num % 10
        return f"{TENS[tens]} {ONES[ones]}".strip()
    return ''


def _three_digits_to_words(num: int) -> str:
    if num == 0:
        return ''
    elif num < 100:
        return _two_digits_to_words(num)
    else:
        hundreds = num // 100
        remainder = num % 100
        if remainder == 0:
            return f"{ONES[hundreds]} Hundred"
        else:
            return f"{ONES[hundreds]} Hundred {_two_digits_to_words(remainder)}"


def amount_to_words_indian(amount) -> str:
    """
    Convert amount to words in Indian numbering system.
    
    Args:
        amount: Numeric value (int, float, Decimal, or string)
    
    Returns:
        String representation in words with "Rupees" and "Paise"
    
    Example:
        amount_to_words_indian(12345.50) -> "Rupees Twelve Thousand Three Hundred Forty Five and Fifty Paise Only"
    """
    try:
        if isinstance(amount, str):
            amount = Decimal(amount.replace(',', ''))
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if amount < 0:
            return "Negative " + amount_to_words_indian(abs(amount))
        
        if amount == 0:
            return "Rupees Zero Only"
        
        rupees = int(amount)
        paise = int((amount - rupees) * 100)
        
        words = []
        
        if rupees > 0:
            words.append("Rupees")
            words.append(_rupees_to_words(rupees))
        
        if paise > 0:
            if rupees > 0:
                words.append("and")
            words.append(_two_digits_to_words(paise))
            words.append("Paise")
        
        words.append("Only")
        
        return ' '.join(filter(None, words))
    
    except Exception:
        return f"Rupees {amount} Only"


def _rupees_to_words(num: int) -> str:
    """Convert rupees part to words using Indian numbering (Lakhs, Crores)."""
    if num == 0:
        return "Zero"
    
    if num < 0:
        return "Negative " + _rupees_to_words(abs(num))
    
    words = []
    
    crores = num // 10000000
    num = num % 10000000
    
    lakhs = num // 100000
    num = num % 100000
    
    thousands = num // 1000
    num = num % 1000
    
    hundreds = num
    
    if crores > 0:
        if crores < 100:
            words.append(_two_digits_to_words(crores))
        else:
            words.append(_three_digits_to_words(crores))
        words.append("Crore")
    
    if lakhs > 0:
        words.append(_two_digits_to_words(lakhs))
        words.append("Lakh")
    
    if thousands > 0:
        words.append(_two_digits_to_words(thousands))
        words.append("Thousand")
    
    if hundreds > 0:
        words.append(_three_digits_to_words(hundreds))
    
    return ' '.join(filter(None, words))


def format_indian_currency(amount) -> str:
    """
    Format amount in Indian number format with commas.
    Example: 1234567.89 -> "12,34,567.89"
    """
    try:
        if isinstance(amount, str):
            amount = Decimal(amount.replace(',', ''))
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        negative = amount < 0
        if negative:
            amount = abs(amount)
        
        rupees = int(amount)
        paise = int((amount - rupees) * 100)
        
        rupees_str = str(rupees)
        
        if len(rupees_str) <= 3:
            formatted = rupees_str
        else:
            last_three = rupees_str[-3:]
            remaining = rupees_str[:-3]
            
            parts = []
            while remaining:
                parts.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            
            formatted = ','.join(parts) + ',' + last_three
        
        result = f"{formatted}.{paise:02d}"
        
        return f"-{result}" if negative else result
    
    except Exception:
        return str(amount)
