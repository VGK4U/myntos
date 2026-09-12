"""
Name Formatter Utility (DC Protocol Compliant)
Normalizes person and partner names to proper title casing.
- Handles initials (e.g. S. Ramakrishna, N. Veeraraju)
- Handles standard titles (Mr., Mrs., Ms., Dr., Shri, Smt)
- Removes accidental punctuation inside words (e.g. mutya;la -> Mutyala)
- Preserves business acronyms (VGK, MNR, EV, LLP, PVT, LTD)
- Hyphenated and combined names
"""

import re
from typing import Optional

KNOWN_ACRONYMS = {'VGK', 'MNR', 'EV', 'ZR', 'ZC', 'PO', 'ETC', 'MD', 'CEO', 'LLP', 'PVT', 'LTD'}
KNOWN_TITLES = {
    'mr': 'Mr.', 'mr.': 'Mr.',
    'mrs': 'Mrs.', 'mrs.': 'Mrs.',
    'ms': 'Ms.', 'ms.': 'Ms.',
    'dr': 'Dr.', 'dr.': 'Dr.',
    'shri': 'Shri', 'shri.': 'Shri',
    'smt': 'Smt', 'smt.': 'Smt'
}

def format_proper_name(name: Optional[str]) -> Optional[str]:
    """
    Formats any name string into proper title casing with Indian naming conventions.
    Returns None if input is None.
    """
    if name is None:
        return None
    s = str(name).strip()
    if not s:
        return ''
        
    # 1. Clean accidental punctuation inside words (e.g. mutya;la -> mutyala)
    s = re.sub(r'(?<=[A-Za-z])[;,:_#]+(?=[A-Za-z])', '', s)
    # Clean remaining punctuation as spaces
    s = re.sub(r'[;,:_#]+', ' ', s)
    
    # 2. If multi-letter word followed by dot and letter (e.g. Abhishek.chinthala), replace dot with space
    s = re.sub(r'([A-Za-z]{2,})\.([A-Za-z])', r'\1 \2', s)
    
    # 3. Single-letter initial with dot attached to next word (e.g. S.Ramakrishna, n.veeraraju) -> S. Ramakrishna
    s = re.sub(r'(^|[\s])([A-Za-z])\.([A-Za-z])', r'\1\2. \3', s)
    
    # 4. Collapse multiple whitespace
    tokens = s.strip().split()
    if not tokens:
        return ''
        
    formatted = []
    for i, tok in enumerate(tokens):
        clean_tok = re.sub(r'[^A-Za-z.]', '', tok)
        clean_lower = clean_tok.lower()
        
        # Title check
        if clean_lower in KNOWN_TITLES:
            formatted.append(KNOWN_TITLES[clean_lower])
            continue
            
        # Acronym check
        if tok.upper() in KNOWN_ACRONYMS:
            formatted.append(tok.upper())
            continue
            
        # Single letter initial: 'B', 'B.', 's', 's.'
        if re.match(r'^[A-Za-z]\.?$', tok):
            letter = tok[0].upper()
            formatted.append(f'{letter}.')
            continue

        # Two-letter initials like 'Ch.' or 'Ch' or 'KV'
        if tok.upper() in ('CH', 'KV', 'SK'):
            formatted.append(tok.capitalize() if tok.upper() == 'CH' else tok.upper())
            continue
            
        # Hyphenated names (e.g. Sai-Ram)
        if '-' in tok:
            formatted.append('-'.join(p.capitalize() for p in tok.split('-')))
            continue
            
        # Word ending in dot
        if tok.endswith('.'):
            core = tok[:-1]
            formatted.append(core.capitalize() + '.')
            continue
            
        # Standard word capitalization
        formatted.append(tok.capitalize())
        
    return ' '.join(formatted)
