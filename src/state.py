import time
from collections import deque
from typing import Dict, List, Tuple

class SignalState:
    """Manages the state of the order book and a rolling window of recent trades.

    This class provides O(1) lookups for order book updates and maintains a 
    10-second window of trade history for high-frequency trading signals.
    """

    def __init__(self) -> None:
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.trades: deque[Tuple[float, str, float]] = deque()

    def update_book(self, side: str, price: float, quantity: float) -> None:
        """Updates the order book. Robust to API variations and prevents float-key bloat."""
        # 1. Robust side matching
        target_dict = self.bids if "bid" in side.lower() else self.asks
        
        # 2. Prevent floating-point duplicate keys by normalizing price to 8 decimal places
        normalized_price = round(price, 8)

        if quantity == 0:
            if normalized_price in target_dict:
                del target_dict[normalized_price]
        else:
            target_dict[normalized_price] = quantity

    def add_trade(self, trade_time: float, side: str, amount: float) -> None:
        self.trades.append((trade_time, side, amount))
        self.cleanup_trades()

    def cleanup_trades(self) -> None:
        now = time.time()
        while self.trades and (now - self.trades[0][0] > 10):
            self.trades.popleft()

    def get_sorted_bids(self, depth: int) -> List[List[float]]:
        sorted_prices = sorted(self.bids.keys(), reverse=True)[:depth]
        return [[p, self.bids[p]] for p in sorted_prices]

    def get_sorted_asks(self, depth: int) -> List[List[float]]:
        sorted_prices = sorted(self.asks.keys())[:depth]
        return [[p, self.asks[p]] for p in sorted_prices]