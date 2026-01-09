from typing import List, Dict
from datetime import datetime
from .postgres import Database


class TradeRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def save_whale_move(
        self,
        wallet: str,
        market_id: str,
        market_question: str,
        side: str,
        size: float,
        price: float
    ) -> int:
        return self.db.insert(
            """
            INSERT INTO whale_moves (wallet, market_id, market_question, side, size, price)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (wallet, market_id, market_question, side, size, price)
        )
    
    def get_unprocessed_moves(self, limit: int = 50) -> List[Dict]:
        return self.db.execute(
            "SELECT * FROM whale_moves WHERE processed = FALSE ORDER BY timestamp DESC LIMIT %s",
            (limit,)
        )
    
    def mark_move_processed(self, move_id: int):
        self.db.execute(
            "UPDATE whale_moves SET processed = TRUE WHERE id = %s",
            (move_id,)
        )
    
    def save_trade(
        self,
        whale_wallet: str,
        market_id: str,
        market_question: str,
        whale_side: str,
        whale_size: float,
        whale_price: float,
        our_side: str,
        our_size: float,
        our_price: float,
        reasoning: str,
        confidence: float,
        status: str = 'pending'
    ) -> int:
        return self.db.insert(
            """
            INSERT INTO trades (
                whale_wallet, market_id, market_question,
                whale_side, whale_size, whale_price,
                our_side, our_size, our_price,
                reasoning, confidence, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                whale_wallet, market_id, market_question,
                whale_side, whale_size, whale_price,
                our_side, our_size, our_price,
                reasoning, confidence, status
            )
        )
    
    def update_trade_status(self, trade_id: int, status: str, executed_at: datetime = None):
        if executed_at:
            self.db.execute(
                "UPDATE trades SET status = %s, executed_at = %s WHERE id = %s",
                (status, executed_at, trade_id)
            )
        else:
            self.db.execute(
                "UPDATE trades SET status = %s WHERE id = %s",
                (status, trade_id)
            )
    
    def close_trade(self, trade_id: int, pnl: float):
        self.db.execute(
            "UPDATE trades SET status = 'closed', closed_at = NOW(), pnl = %s WHERE id = %s",
            (pnl, trade_id)
        )
    
    def get_open_trades(self) -> List[Dict]:
        return self.db.execute(
            "SELECT * FROM trades WHERE status IN ('pending', 'executed') ORDER BY created_at DESC"
        )
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        return self.db.execute(
            "SELECT * FROM trades ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
    
    def get_trades_by_whale(self, wallet: str, limit: int = 50) -> List[Dict]:
        return self.db.execute(
            "SELECT * FROM trades WHERE whale_wallet = %s ORDER BY created_at DESC LIMIT %s",
            (wallet, limit)
        )
    
    def get_pnl_summary(self) -> Dict:
        result = self.db.execute_one(
            """
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl
            FROM trades WHERE status = 'closed'
            """
        )
        return result or {}
    
    def save_brain_bet(
        self,
        symbol: str,
        timeframe: str,
        side: str,
        entry_price: float,
        volume: float,
        brain_reason: str,
        brain_decision: str,
        order_id: str = None,
        size: float = None,
        status: str = 'pending'
    ) -> int:
        return self.db.insert(
            """
            INSERT INTO brain_bets (symbol, timeframe, side, entry_price, volume, 
                brain_reason, brain_decision, order_id, size, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (symbol, timeframe, side, entry_price, volume, brain_reason, 
             brain_decision, order_id, size, status)
        )
    
    def update_brain_bet(self, bet_id: int, current_price: float, pnl: float, status: str):
        self.db.execute(
            """
            UPDATE brain_bets 
            SET current_price = %s, pnl = %s, status = %s, resolved_at = NOW()
            WHERE id = %s
            """,
            (current_price, pnl, status, bet_id)
        )
    
    def get_brain_bets(self, status: str = None, limit: int = 50) -> List[Dict]:
        if status:
            return self.db.execute(
                "SELECT * FROM brain_bets WHERE status = %s ORDER BY created_at DESC LIMIT %s",
                (status, limit)
            )
        return self.db.execute(
            "SELECT * FROM brain_bets ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
    
    def get_brain_pnl(self) -> Dict:
        result = self.db.execute_one(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl
            FROM brain_bets WHERE status IN ('won', 'lost')
            """
        )
        return result or {}
