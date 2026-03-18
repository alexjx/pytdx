# PyTDX Analysis Notes

This directory contains analysis documentation for the PyTDX project.

## Files

| File | Description |
|------|-------------|
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | Comprehensive architecture and protocol documentation |
| [SERVER_ANALYSIS.md](SERVER_ANALYSIS.md) | Server list comparison between repo and ZSZQ software |

## Quick Reference

### Updated Server List (from ZSZQ PC Software)

#### Quote Servers (Port 7709)
- 招商证券上海云: `47.100.132.162:7709` ✓ Tested
- 招商证券上海云1: `39.108.28.83:7709` ✓ Tested
- 招商证券北京云1: `39.105.251.234:7709` ✓ Tested
- 招商证券广州云1: `111.230.189.225:7709` ✓ Tested

#### Extended Market Servers (Port 7727)
- 扩展行情-上海云1: `101.132.165.164:7727` ✓ Tested
- 扩展行情-深圳云1: `193.112.226.233:7727` ✓ Tested
- 扩展行情-北京云1: `8.141.17.79:7727` ✓ Tested

## Testing Methodology / 测试方法

### 1. Quote Servers (Port 7709) / 行情服务器

**Test Logic:**
1. Connect to server via TCP port 7709
2. Send `get_security_quotes` command for stock 000001 (平安银行)
3. Verify response contains valid price data
4. Measure connection latency

**Test Code:**
```python
from pytdx.hq import TdxHq_API
import time

api = TdxHq_API()
start = time.time()

if api.connect('47.100.132.162', 7709):
    quotes = api.get_security_quotes([(0, '000001')])  # 0=Shenzhen, 000001=平安银行
    latency = (time.time() - start) * 1000

    if quotes and len(quotes) > 0:
        print(f"✓ Server working")
        print(f"  Price: {quotes[0].get('price')}")
        print(f"  Latency: {latency:.1f}ms")

    api.disconnect()
```

**Success Criteria:**
- TCP connection established
- Response contains valid quote data
- Price field is present and reasonable (e.g., 10.94 for 000001)

---

### 2. Extended Market Servers (Port 7727) / 扩展行情服务器

**Test Logic:**
1. Connect to server via TCP port 7727
2. Send `get_instrument_count` command
3. Verify response contains valid instrument count
4. Measure connection latency

**Test Code:**
```python
from pytdx.exhq import TdxExHq_API
import time

api = TdxExHq_API()
start = time.time()

if api.connect('101.132.165.164', 7727):
    count = api.get_instrument_count()
    latency = (time.time() - start) * 1000

    print(f"✓ Server working")
    print(f"  Instruments: {count}")
    print(f"  Latency: {latency:.1f}ms")

    api.disconnect()
```

**Success Criteria:**
- TCP connection established
- Response contains instrument count > 0
- Typical count: 90,000 - 110,000 instruments

---

### 3. Full Test Script / 完整测试脚本

```python
from pytdx.hq import TdxHq_API
from pytdx.exhq import TdxExHq_API
import time

# Test quote servers
quote_servers = [
    ('招商证券上海云', '47.100.132.162', 7709),
    ('招商证券北京云1', '39.105.251.234', 7709),
]

print("Testing Quote Servers...")
for name, ip, port in quote_servers:
    api = TdxHq_API()
    try:
        start = time.time()
        if api.connect(ip, port):
            quotes = api.get_security_quotes([(0, '000001')])
            latency = (time.time() - start) * 1000
            print(f"✓ {name} ({latency:.1f}ms) - Price: {quotes[0].get('price')}")
            api.disconnect()
        else:
            print(f"✗ {name} - Connection failed")
    except Exception as e:
        print(f"✗ {name} - Error: {e}")

# Test extended market servers
ex_servers = [
    ('扩展行情-上海云1', '101.132.165.164', 7727),
    ('扩展行情-深圳云1', '193.112.226.233', 7727),
]

print("\nTesting Extended Market Servers...")
for name, ip, port in ex_servers:
    api = TdxExHq_API()
    try:
        start = time.time()
        if api.connect(ip, port):
            count = api.get_instrument_count()
            latency = (time.time() - start) * 1000
            print(f"✓ {name} ({latency:.1f}ms) - Count: {count}")
            api.disconnect()
        else:
            print(f"✗ {name} - Connection failed")
    except Exception as e:
        print(f"✗ {name} - Error: {e}")
```

---

## Test Results / 测试结果

| Server Type | IP:Port | Latency | Status |
|-------------|---------|---------|--------|
| 招商证券上海云 | 47.100.132.162:7709 | ~61ms | ✓ Working |
| 招商证券上海云1 | 39.108.28.83:7709 | ~164ms | ✓ Working |
| 招商证券北京云1 | 39.105.251.234:7709 | ~139ms | ✓ Working |
| 招商证券广州云1 | 111.230.189.225:7709 | ~144ms | ✓ Working |
| 扩展行情-上海云1 | 101.132.165.164:7727 | ~43ms | ✓ Working |
| 扩展行情-深圳云1 | 193.112.226.233:7727 | ~95ms | ✓ Working |
| 扩展行情-北京云1 | 8.141.17.79:7727 | ~83ms | ✓ Working |
