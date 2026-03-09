import csv
import os
import time
import logging
from typing import Dict, Any, List, Optional
from src.state import SignalState
from src.math_tools import MicroMath

# Configuration for logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SniperBrain")


class SniperBrain:
    """The orchestration engine for HFT signal processing and trade simulation.

    This class monitors the watchlist for Telegram signals, evaluates market
    microstructure metrics (OBI, OFI), and manages simulated positions.

    Attributes:
        active_watchlist (Dict[str, Dict]): Symbols to watch with their signal parameters.
        simulated_positions (Dict[str, Dict]): Currently open simulated trades.
        log_file (str): Path to the CSV file for backtest results.
    """

    def __init__(self, log_dir: str = "logs") -> None:
        """Initializes the SniperBrain and ensures the log directory exists.

        Args:
            log_dir (str): Directory where CSV logs will be stored.
        """
        self.active_watchlist: Dict[str, Dict[str, Any]] = {}
        self.simulated_positions: Dict[str, Dict[str, Any]] = {}
        self.log_file = os.path.join(log_dir, "backtest_results.csv")

        # Create logs directory and CSV header if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Symbol", "Side", "Entry Price", 
                    "Exit Price", "P/L %", "Leverage", "Result"
                ])

    def add_to_watchlist(self, symbol: str, side: str, leverage: int, entry: float, tp: float, sl: Optional[float] = None) -> None:
        """Adds a new signal from Telegram to the active watchlist.

        Args:
            symbol (str): The ticker (e.g., 'PHA').
            side (str): 'Long' or 'Short'.
            leverage (int): Leverage multiplier (e.g., 20).
            entry (float): Target entry price.
            tp (float): Take profit target.
            sl (float, optional): Stop loss price. Defaults to 1% from entry if None.
        """
        # Default SL logic if not provided: 1% from entry
        if sl is None:
            sl = entry * 0.99 if side.lower() == "long" else entry * 1.01

        self.active_watchlist[symbol.upper()] = {
            "entry_target": entry,
            "tp_target": tp,
            "sl_target": sl,
            "side": side.lower(),
            "leverage": leverage
        }
        logger.info(f"Watchlist Updated: {symbol} @ {entry} (TP: {tp}, SL: {sl})")

    def update(self, symbol: str, state: SignalState) -> None:
        """The heartbeat of the sniper. Processes state updates and manages trades.

        Args:
            symbol (str): The symbol being updated.
            state (SignalState): The current market state for the symbol.
        """
        symbol = symbol.upper()
        
        # 1. Safety Check: Data Freshness
        if not state.trades:
            return
            
        last_trade_time = state.trades[-1][0]
        if (time.time() - last_trade_time) > 2.0:
            # Data is stale, skip execution logic
            return

        # 2. Get Current Market Price (Mid Price)
        best_bid = state.get_sorted_bids(1)
        best_ask = state.get_sorted_asks(1)
        if not best_bid or not best_ask:
            return
            
        current_price = (best_bid[0][0] + best_ask[0][0]) / 2.0

        # 3. Manage Existing Positions
        if symbol in self.simulated_positions:
            self._check_exit_conditions(symbol, current_price)
            return

        # 4. Evaluate Entry Conditions
        if symbol in self.active_watchlist:
            self._evaluate_entry(symbol, state, current_price)

    def _evaluate_entry(self, symbol: str, state: SignalState, current_price: float) -> None:
        """Checks if OBI/OFI conditions are met to trigger a trade.

        Conditions: OBI > 0.8 OR OFI > 500 (based on user request).
        """
        signal = self.active_watchlist[symbol]
        
        # Calculate Microstructure Metrics
        obi = MicroMath.calculate_obi(state, depth=5)
        ofi = MicroMath.calculate_ofi(state)

        # Entry logic: High pressure detection
        # Note: In a real bot, we'd check if OBI/OFI aligns with the 'side' (Long vs Short)
        # Here we follow the user's specific threshold request.
        if obi > 0.8 or ofi > 500:
            logger.info(f"Sniper Entry Triggered: {symbol} | OBI: {obi:.2f} | OFI: {ofi:.0f}")
            
            self.simulated_positions[symbol] = {
                "entry_price": current_price,
                "side": signal["side"],
                "leverage": signal["leverage"],
                "tp_target": signal["tp_target"],
                "sl_target": signal["sl_target"],
                "timestamp": time.time()
            }
            
            # Remove from watchlist once position is open
            del self.active_watchlist[symbol]

    def _check_exit_conditions(self, symbol: str, current_price: float) -> None:
        """Checks if current price has hit TP or SL targets."""
        pos = self.simulated_positions[symbol]
        side = pos["side"]
        tp = pos["tp_target"]
        sl = pos["sl_target"]

        closed = False
        result = ""

        if side == "long":
            if current_price >= tp:
                closed, result = True, "TP"
            elif current_price <= sl:
                closed, result = True, "SL"
        else: # short
            if current_price <= tp:
                closed, result = True, "TP"
            elif current_price >= sl:
                closed, result = True, "SL"

        if closed:
            self._close_position(symbol, current_price, result)

    def _close_position(self, symbol: str, exit_price: float, result: str) -> None:
        """Logs the trade result to CSV and cleans up state."""
        pos = self.simulated_positions[symbol]
        entry_price = pos["entry_price"]
        leverage = pos["leverage"]
        side = pos["side"]

        # Calculate P/L
        raw_pl = (exit_price - entry_price) / entry_price
        if side == "short":
            raw_pl *= -1
        
        leveraged_pl = raw_pl * leverage * 100  # Percentage

        # Log to CSV
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                symbol, side, entry_price, exit_price, 
                f"{leveraged_pl:.2f}%", leverage, result
            ])

        logger.info(f"Position Closed: {symbol} | Result: {result} | P/L: {leveraged_pl:.2f}%")
        del self.simulated_positions[symbol]
