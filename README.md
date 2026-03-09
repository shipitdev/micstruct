# ClickinBot: HFT Microstructure Sniper 🚀

ClickinBot is an event-driven, High-Frequency Trading (HFT) execution engine designed to "snipe" entries based on real-time market microstructure signals. It integrates Binance L2 Order Book data with Telegram-based trading signals, using Order Book Imbalance (OBI) and Order Flow Imbalance (OFI) to confirm high-probability entry points.

---

## 🏗 Architecture Overview

The system employs a **Producer-Consumer** architecture mediated by an asynchronous state container:

1.  **Ingestion Layer (Producers):**
    *   **StreamManager:** Maintains low-latency WebSocket connections to Binance for `@depth` (L2 Order Book) and `@aggTrade` streams.
    *   **TelegramManager:** Asynchronously monitors specific alpha channels for formatted trading signals using Regex-based parsing.
2.  **State Management:**
    *   **SignalState:** A thread-safe, O(1) container utilizing `collections.deque` for rolling 10s trade windows and normalized price maps for the order book.
3.  **Quantitative Engine:**
    *   **MicroMath:** A stateless utility library calculating high-precision HFT metrics (Spread, OBI, OFI, and Ask Pull/Cancelation).
4.  **Execution Logic (Orchestrator):**
    *   **SniperBrain:** Manages the active watchlist, evaluates microstructure triggers (OBI > 0.8 or OFI > 500), and simulates trades with Take-Profit (TP) and Stop-Loss (SL) logic.

---

## 📊 Quantitative Metrics

ClickinBot focuses on lead indicators rather than lagging price action:

*   **Order Book Imbalance (OBI):** Measures the volume disparity between the bid and ask sides.
    *   $OBI = \frac{Volume_{Bid} - Volume_{Ask}}{Volume_{Total}}$
*   **Order Flow Imbalance (OFI):** Tracks the net aggressive buying vs. selling pressure over a rolling 1-second window.
*   **Ask Pull Detection:** Detects rapid order cancellations at the ask, often a precursor to "spoofing" reversals or breakout momentum.

---

## 🚀 Getting Started

### Prerequisites

*   Python 3.8+
*   Binance Account (for Public WebSocket access)
*   Telegram API Credentials ([my.telegram.org](https://my.telegram.org))

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/clickinbot.git
    cd clickinbot
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure environment variables in a `.env` file:
    ```env
    TELEGRAM_API_ID=1234567
    TELEGRAM_API_HASH='your_api_hash'
    TELEGRAM_CHANNEL='@YourSignalChannel'
    ```

### Running the Bot

To start the main orchestrator:
```bash
python main.py
```

---

## 📂 Project Structure

```text
├── src/
│   ├── brain.py        # Decision engine & trade simulation
│   ├── math_tools.py   # HFT quantitative formulas
│   ├── state.py        # Thread-safe market state container
│   ├── stream.py       # Binance WebSocket manager
│   └── telegram.py     # Signal ingestion & parsing
├── logs/
│   └── backtest_results.csv  # Simulated trade logs
├── main.py             # Entry point & orchestrator
└── GEMINI.md           # Internal development roadmap
```

---

## ⚠️ Disclaimer

This bot is currently in **Simulated Mode**. All trades are logged to `logs/backtest_results.csv` for performance analysis and backtesting. Use at your own risk. Past performance does not guarantee future results.

---

## 🛠 Current Progress

- [x] **Asynchronous State Management** (O(1) lookups)
- [x] **L2 Order Book Ingestion** (100ms updates)
- [x] **Telegram Signal Parsing** (Regex-based)
- [x] **Microstructure Triggers** (OBI/OFI Implementation)
- [x] **Main Orchestration Layer**
- [ ] **Live Execution API** (Integration with Binance Futures API)
- [ ] **Performance Dashboard** (Real-time P/L visualization)
