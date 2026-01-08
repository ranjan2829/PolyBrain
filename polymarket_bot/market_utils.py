from datetime import datetime, timezone, timedelta
from typing import Dict


def generate_market_slug(timestamp: int, symbol: str = 'BTC', timeframe: str = '15m') -> str:
    symbol_lower = symbol.lower()
    
    if timeframe == '1h':
        et_offset = timedelta(hours=-5)
        et_timezone_obj = timezone(et_offset)
        dt = datetime.fromtimestamp(timestamp, tz=et_timezone_obj)
        
        month_name = dt.strftime('%B').lower()
        day = dt.day
        hour_12 = dt.strftime('%I').lstrip('0') or '12'
        am_pm = dt.strftime('%p').lower()
        
        symbol_map = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'XRP': 'xrp'}
        symbol_name = symbol_map.get(symbol, symbol_lower)
        
        return f"{symbol_name}-up-or-down-{month_name}-{day}-{hour_12}{am_pm}-et"
    else:
        timeframe_slug = {'15m': '15m', '4h': '4h'}.get(timeframe, '15m')
        return f"{symbol_lower}-updown-{timeframe_slug}-{timestamp}"


def get_interval_timestamps(timeframe: str) -> tuple:
    interval_durations = {'15m': 900, '1h': 3600, '4h': 14400}
    interval_duration = interval_durations.get(timeframe, 900)
    
    et_offset = timedelta(hours=-5)
    et_timezone_obj = timezone(et_offset)
    now_ts = int(datetime.now(et_timezone_obj).timestamp())
    
    current_interval = (now_ts // interval_duration) * interval_duration
    next_interval = current_interval + interval_duration
    
    intervals = [current_interval, next_interval]
    if timeframe == '1h':
        intervals.append(current_interval - interval_duration)
    
    return intervals


def normalize_market(market: Dict) -> Dict:
    condition_id = market.get('conditionId') or market.get('condition_id')
    if not condition_id:
        return None
    
    return {
        'id': market.get('question_id') or market.get('id') or condition_id,
        'conditionId': condition_id,
        'question': market.get('question', 'Unknown'),
        'slug': market.get('slug', '') or market.get('market_slug', ''),
        'active': market.get('active', False),
        'closed': market.get('closed', False),
        'volume': float(market.get('volume', 0) or 0),
        'liquidity': float(market.get('liquidity', 0) or 0),
        'outcomes': market.get('outcomes', []) or [],
    }


def parse_json_fields(market: Dict) -> Dict:
    for field in ['clobTokenIds', 'outcomes', 'outcomePrices']:
        if field in market and isinstance(market[field], str):
            import json
            market[field] = json.loads(market[field])
    return market

