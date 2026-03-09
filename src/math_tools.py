import time
from typing import Dict
from src.state import SignalState


class MicroMath:
    """Utility class for high-frequency trading mathematical calculations.

    This class provides static methods for calculating order book metrics
    such as spread, imbalance, and flow. It is stateless and requires
    a SignalState instance for all operations.
    """

    @staticmethod
    def calculate_spread(state: SignalState) -> float:
        """Calculates the current bid-ask spread.

        Args:
            state (SignalState): The current market state.

        Returns:
            float: The difference between the best ask and best bid. 
                   Returns 0.0 if either side is empty.
        """
        best_bid = state.get_sorted_bids(1)
        best_ask = state.get_sorted_asks(1)

        if not best_bid or not best_ask:
            return 0.0

        return best_ask[0][0] - best_bid[0][0]

    @staticmethod
    def calculate_obi(state: SignalState, depth: int = 5) -> float:
        """Calculates the Order Book Imbalance (OBI).

        OBI = (Bid Volume - Ask Volume) / (Bid Volume + Ask Volume)
        The result is bounded between -1.0 and 1.0.

        Args:
            state (SignalState): The current market state.
            depth (int): The number of price levels to consider.

        Returns:
            float: The calculated imbalance. Returns 0.0 if total volume is zero.
        """
        bids = state.get_sorted_bids(depth)
        asks = state.get_sorted_asks(depth)

        if not bids and not asks:
            return 0.0

        bid_vol = sum(level[1] for level in bids)
        ask_vol = sum(level[1] for level in asks)

        total_vol = bid_vol + ask_vol
        if total_vol == 0:
            return 0.0

        return (bid_vol - ask_vol) / total_vol

    @staticmethod
    def calculate_ofi(state: SignalState) -> float:
        """Calculates the Order Flow Imbalance (OFI) for the last 1.0 second.

        Sums volume where buy trades are positive and sell trades are negative.

        Args:
            state (SignalState): The current market state.

        Returns:
            float: The net order flow imbalance.
        """
        now = time.time()
        # OFI uses buy (+1) and sell (-1)
        # Note: A 'buy' trade hits the ask, a 'sell' trade hits the bid.
        net_flow = 0.0
        for t_time, side, amount in reversed(state.trades):
            if now - t_time > 1.0:
                break
            
            if side.lower() == 'buy':
                net_flow += amount
            elif side.lower() == 'sell':
                net_flow -= amount
                
        return net_flow

    @staticmethod
    def calculate_ask_pull(state: SignalState, prev_asks: Dict[float, float]) -> float:
        """Calculates the 'pull' (cancellation) volume from the ask side.

        If a price level's volume decreases and no trade occurred at that price,
        the difference is considered a 'pull'.

        Args:
            state (SignalState): The current market state.
            prev_asks (Dict[float, float]): The ask dictionary from the previous update.

        Returns:
            float: The total volume of pulled/cancelled ask orders.
        """
        if not prev_asks:
            return 0.0

        pull_volume = 0.0
        
        # Identify buy trades in the last small window to account for executions.
        # Since SignalState doesn't store price per trade, we check for volume decreases
        # that aren't explained by the presence of any recent buy trades.
        # Logic: If price volume decreases and no buy trades exist, it's a pull.
        # If buy trades exist, we conservatively only count decreases beyond trade volume.
        
        now = time.time()
        recent_buy_vol = sum(t[2] for t in state.trades if t[1].lower() == 'buy' and now - t[0] < 0.1)

        for price, prev_qty in prev_asks.items():
            current_qty = state.asks.get(price, 0.0)
            
            if current_qty < prev_qty:
                diff = prev_qty - current_qty
                
                # If no buy trades occurred recently, the entire diff is a pull.
                # If buy trades occurred, we subtract them from the diff to be safe.
                # (This is an approximation due to lack of price-specific trade data).
                if recent_buy_vol <= 0:
                    pull_volume += diff
                else:
                    unaccounted_drop = max(0.0, diff - recent_buy_vol)
                    pull_volume += unaccounted_drop
                    recent_buy_vol = max(0.0, recent_buy_vol - diff)

        return pull_volume
