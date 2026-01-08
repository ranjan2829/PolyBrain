"""Market filtering utilities."""
from typing import List, Dict


def filter_financial_markets(markets: List[Dict], min_volume: float) -> List[Dict]:
    """Filter high-volume financial markets."""
    financial_keywords = [
        'sp500', 'sp 500', 's&p', 'dow', 'nasdaq', 'stock', 'equity',
        'financial', 'fed', 'interest rate', 'inflation', 'gdp', 'treasury',
        'bond', 'yield', 'federal reserve', 'unemployment', 'cpi', 'ppi',
        'federal spending', 'budget'
    ]
    
    filtered = []
    for m in markets:
        question = str(m.get('question', '')).lower()
        tags = [str(t).lower() for t in (m.get('tags', []) or [])]
        tag_str = ' '.join(tags)
        
        is_financial = any(kw in question for kw in financial_keywords) or any(kw in tag_str for kw in financial_keywords)
        vol = float(m.get('volume', 0) or 0)
        
        if is_financial and vol >= min_volume:
            filtered.append(m)
    
    return filtered

