import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from ..config import os

DATABASE_URL = os.getenv('DATABASE_URL')


@dataclass
class Trade:
    id: Optional[int]
    whale_wallet: str
    market_id: str
    market_question: str
    side: str
    size: float
    price: float
    our_size: float
    our_price: float
    reasoning: str
    confidence: float
    status: str
    created_at: datetime
    executed_at: Optional[datetime]
    pnl: Optional[float]


@dataclass
class WhaleMove:
    id: Optional[int]
    wallet: str
    market_id: str
    market_question: str
    side: str
    size: float
    price: float
    timestamp: datetime
    processed: bool


class Database:
    def __init__(self, url: str = None):
        self.url = url or DATABASE_URL
        self.conn = None
    
    def connect(self):
        if not self.url:
            raise ValueError("DATABASE_URL not set")
        self.conn = psycopg2.connect(self.url)
        return self
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def init_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS whale_moves (
                    id SERIAL PRIMARY KEY,
                    wallet VARCHAR(42) NOT NULL,
                    market_id VARCHAR(100) NOT NULL,
                    market_question TEXT,
                    side VARCHAR(10) NOT NULL,
                    size DECIMAL(20, 8) NOT NULL,
                    price DECIMAL(10, 6) NOT NULL,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    whale_wallet VARCHAR(42) NOT NULL,
                    market_id VARCHAR(100) NOT NULL,
                    market_question TEXT,
                    whale_side VARCHAR(10) NOT NULL,
                    whale_size DECIMAL(20, 8) NOT NULL,
                    whale_price DECIMAL(10, 6) NOT NULL,
                    our_side VARCHAR(10) NOT NULL,
                    our_size DECIMAL(20, 8) NOT NULL,
                    our_price DECIMAL(10, 6),
                    reasoning TEXT,
                    confidence DECIMAL(5, 4),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    executed_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ,
                    pnl DECIMAL(20, 8)
                );
                
                CREATE INDEX IF NOT EXISTS idx_whale_moves_wallet ON whale_moves(wallet);
                CREATE INDEX IF NOT EXISTS idx_whale_moves_processed ON whale_moves(processed);
                CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
                CREATE INDEX IF NOT EXISTS idx_trades_whale ON trades(whale_wallet);
                
                CREATE TABLE IF NOT EXISTS brain_bets (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    side VARCHAR(10) NOT NULL,
                    entry_price DECIMAL(10, 4) NOT NULL,
                    volume DECIMAL(20, 2),
                    brain_reason TEXT,
                    brain_decision VARCHAR(10) NOT NULL,
                    order_id VARCHAR(100),
                    size DECIMAL(20, 4),
                    status VARCHAR(20) DEFAULT 'pending',
                    current_price DECIMAL(10, 4),
                    pnl DECIMAL(10, 4),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ
                );
                
                CREATE INDEX IF NOT EXISTS idx_brain_bets_status ON brain_bets(status);
            """)
            self.conn.commit()
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            self.conn.commit()
            return []
    
    def execute_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        results = self.execute(query, params)
        return results[0] if results else None
    
    def insert(self, query: str, params: tuple = None) -> int:
        with self.conn.cursor() as cur:
            cur.execute(query + " RETURNING id", params)
            result = cur.fetchone()
            self.conn.commit()
            return result[0] if result else None
