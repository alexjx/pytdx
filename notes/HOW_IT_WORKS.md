# PyTDX - How It Works

A comprehensive guide to understanding the PyTDX codebase architecture and implementation.

## Overview

PyTDX is a pure Python implementation of the **TDX (通达信/Tongdaxin) stock market data protocol**. It provides programmatic access to Chinese stock market data including:

- Real-time quotes (A-shares, B-shares, indices)
- Historical K-line data (1min, 5min, 15min, 30min, 1hour, daily, weekly, monthly)
- Intraday minute-level data
- Transaction details (tick data)
- Financial statements and company information
- Extended market data (futures, options, international markets)

---

## Architecture

```
pytdx/
├── hq.py                 # Standard Quote API (TdxHq_API)
├── exhq.py               # Extended Quote API (TdxExHq_API)
├── base_socket_client.py # TCP socket connection handling
├── heartbeat.py          # Connection keep-alive mechanism
├── helper.py             # Data encoding/decoding utilities
├── errors.py             # Exception definitions
├── params.py             # Protocol constants
├── log.py                # Logging configuration
│
├── parser/               # Protocol command parsers
│   ├── base.py           # BaseParser class
│   ├── setup.py          # Connection setup commands
│   ├── get_security_*.py # Various data retrieval parsers
│   └── ...
│
├── reader/               # Local data file readers
│   ├── daily_bar_reader.py   # .day files (daily K-lines)
│   ├── min_bar_reader.py     # .lc1/.lc5 files (minute data)
│   └── ...
│
├── trade/                # Trading API (HTTP-based)
│   └── ...
│
├── crawler/              # Data crawlers
│   └── history_financial_crawler.py
│
├── config/               # Server configurations
│   └── hosts.py          # Available TDX server list
│
├── pool/                 # Connection pooling
│   └── ...
│
└── bin/                  # CLI tools
    ├── hqget.py          # Interactive data retrieval
    ├── hqreader.py       # Local file reader
    └── hqbenchmark.py    # Performance testing
```

---

## Core Components

### 1. Network Layer (`base_socket_client.py`)

The foundation of all network communication:

```python
class BaseSocketClient:
    """Manages TCP socket connection to TDX servers."""

    def connect(self, host, port): ...
    def disconnect(self): ...
    def send(self, data): ...
    def receive(self, size): ...
```

**Key Features:**
- TCP socket connections (default port: 7709)
- Automatic reconnection
- Traffic statistics tracking
- Connection state management

### 2. Quote APIs (`hq.py`, `exhq.py`)

#### TdxHq_API - Standard Market Data

```python
from pytdx.hq import TdxHq_API

api = TdxHq_API()
if api.connect('119.147.212.81', 7709):
    # Get real-time quotes
    quotes = api.get_security_quotes([(0, '000001'), (1, '600000')])

    # Get daily K-lines
    bars = api.get_security_bars(9, 0, '000001', 0, 100)

    # Get stock list
    stocks = api.get_security_list(1, 0)

    api.disconnect()
```

#### TdxExHq_API - Extended Market Data

For futures, options, and international markets:

```python
from pytdx.exhq import TdxExHq_API

api = TdxExHq_API()
if api.connect('112.74.214.43', 7727):
    # Get instrument count
    count = api.get_instrument_count()

    # Get futures quotes
    quotes = api.get_instrument_quotes(8, 0, 100)

    api.disconnect()
```

### 3. Protocol Parsers (`parser/`)

Each parser handles a specific TDX protocol command:

| Parser | Purpose |
|--------|---------|
| `GetSecurityQuotes` | Real-time stock quotes |
| `GetSecurityBars` | K-line/OHLCV data |
| `GetSecurityList` | Stock listings by market |
| `GetMinuteTimeData` | Intraday minute data |
| `GetHistoryMinuteTimeData` | Historical minute data |
| `GetTransactionData` | Tick-by-tick transactions |
| `GetFinancialInfo` | Company financial data |

**Parser Structure:**

```python
class BaseParser:
    def setup(self):           # Initialize parameters
    def call(self):            # Build request packet
    def parse(self, data):     # Parse response data
    def getResponse(self):     # Return structured result
```

### 4. Local Data Readers (`reader/`)

Read TDX's proprietary binary file formats:

| File Type | Extension | Reader |
|-----------|-----------|--------|
| Daily K-lines | `.day` | `TdxDailyBarReader` |
| 1-minute data | `.lc1` | `TdxLC1BarReader` |
| 5-minute data | `.lc5` | `TdxLC5BarReader` |

```python
from pytdx.reader import TdxDailyBarReader

reader = TdxDailyBarReader()
df = reader.get_df('/path/to/vipdoc/sz/lday/sz000001.day')
```

---

## Protocol Details

### Connection Sequence

1. **TCP Handshake**: Connect to server on port 7709
2. **Setup Commands**: Send 3 initialization packets
   - Setup command 1: Client capabilities
   - Setup command 2: Client identification
   - Setup command 3: Final acknowledgment
3. **Data Requests**: Send specific command codes
4. **Heartbeat**: Periodic keep-alive (every 10 seconds)

### Packet Structure

```
┌─────────────────────────────────────────────────────┐
│ Header (16 bytes)                                   │
├─────────┬─────────┬─────────┬─────────┬─────────────┤
│ 0x0C    │ 0x00    │ CmdHi   │ CmdLo   │ DataSize    │
│ (1 byte)│ (1 byte)│ (1 byte)│ (1 byte)│ (4 bytes)   │
├─────────┴─────────┴─────────┴─────────┴─────────────┤
│ Body (zlib-compressed data)                         │
└─────────────────────────────────────────────────────┘
```

### Data Encoding

Prices use **delta encoding** for compression:

```python
# Price reconstruction
open = base_price + delta_open
high = open + delta_high
low = open + delta_low
close = open + delta_close
```

Large volumes use **compact encoding**:

```python
# Volume decoding
if volume_flag & 0x80:
    volume = (volume_flag & 0x7F) << 16 | next_2_bytes
```

---

## Connection Pooling (`pool/`)

For high-availability applications:

```python
from pytdx.pool.hq_pool import TdxHqPool_API

# Create connection pool
pool = TdxHqPool_API(
    hosts=[('119.147.212.81', 7709), ('113.105.73.88', 7709)]
)

# Automatic failover
with pool.get_connection() as api:
    data = api.get_security_bars(9, 0, '000001', 0, 100)
```

---

## Trading API (`trade/`)

HTTP-based trading interface (requires TdxTradeServer):

```python
from pytdx.trade import TdxTradeApi

api = TdxTradeApi('http://localhost:7708')

# Login
api.logon('account', 'password')

# Query positions
positions = api.query_data(0)

# Place order
order_id = api.send_order(
    exchange_type=1,  # Shanghai
    stock_code='600000',
    price=10.0,
    quantity=100,
    direction=0  # Buy
)
```

---

## Server Configuration (`config/hosts.py`)

Available server groups with geographic distribution:

```python
# Standard quote servers
TDX_HQ_HOSTS = [
    ('119.147.212.81', 7709),  # Shenzhen
    ('113.105.73.88', 7709),   # Shenzhen
    ('14.215.128.18', 7709),   # Guangzhou
    # ... more servers
]

# Extended quote servers (futures/options)
TDX_EXHQ_HOSTS = [
    ('112.74.214.43', 7727),
    # ... more servers
]
```

---

## CLI Tools

### hqget - Interactive Data Retrieval

```bash
# Connect and get quotes
uv run hqget

# Select server, then use commands:
# > get_security_bars 9 0 000001 0 100
# > get_security_quotes 0 000001 1 600000
```

### hqreader - Local File Reader

```bash
uv run hqreader --dir /path/to/vipdoc --output data.csv
```

### hqbenchmark - Performance Testing

```bash
uv run hqbenchmark --count 100 --server 119.147.212.81
```

---

## Data Formats

### K-line (OHLCV) Structure

| Field | Type | Description |
|-------|------|-------------|
| datetime | int | YYYYMMDD or HHMMSS |
| open | float | Opening price |
| high | float | Highest price |
| low | float | Lowest price |
| close | float | Closing price |
| volume | int | Trading volume (shares) |
| amount | float | Trading amount (yuan) |

### Real-time Quote Structure

| Field | Type | Description |
|-------|------|-------------|
| code | str | Stock code |
| market | int | 0=Shenzhen, 1=Shanghai |
| price | float | Current price |
| open/high/low | float | OHLC data |
| bid1-bid10 | float | Bid prices |
| ask1-ask10 | float | Ask prices |
| bid_vol1-10 | int | Bid volumes |
| ask_vol1-10 | int | Ask volumes |

---

## K-line Categories

| Category | Description |
|----------|-------------|
| 0 | 5-minute |
| 1 | 15-minute |
| 2 | 30-minute |
| 3 | 1-hour |
| 4 | Daily |
| 5 | Weekly |
| 6 | Monthly |
| 7 | 1-minute |
| 8 | 1-minute (extended) |
| 9 | Daily |
| 10 | Weekly |
| 11 | Monthly |

---

## Error Handling

```python
from pytdx.errors import (
    TdxError,           # Base exception
    TdxConnectionError, # Network issues
    TdxDataError,       # Invalid data
    TdxTimeoutError,    # Request timeout
)

try:
    api.connect(host, port)
except TdxConnectionError as e:
    print(f"Connection failed: {e}")
```

---

## Threading Support

Enable multi-threading via environment variable:

```bash
export TDX_MT=1  # Enable multithreading
```

---

## Dependencies

- **click**: CLI framework
- **pandas**: Data structures (DataFrame output)
- **six**: Python 2/3 compatibility
- **cryptography**: Encryption for trading API
- **cython** (optional): Performance optimization

---

## Quick Reference

```python
from pytdx.hq import TdxHq_API

# Standard workflow
api = TdxHq_API(heartbeat=True)  # Enable auto-heartbeat

if api.connect('119.147.212.81', 7709):
    try:
        # Real-time quotes
        quotes = api.get_security_quotes([(0, '000001')])

        # Daily K-lines (last 100 bars)
        bars = api.get_security_bars(9, 0, '000001', 0, 100)

        # Intraday minute data
        minutes = api.get_minute_time_data(0, '000001')

        # Tick data
        ticks = api.get_transaction_data(0, '000001', 0, 100)

        # Financial data
        finance = api.get_finance_info(0, '000001')

    finally:
        api.disconnect()
```
