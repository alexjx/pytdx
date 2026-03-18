# Server List Analysis - PyTDX vs ZSZQ PC Software

## Summary

The repository **does contain** a host list in `pytdx/config/hosts.py` with ~100+ servers.

The ZSZQ (招商证券) PC software at `/mnt/c/zd_zsone/` contains **more up-to-date** server lists in `connect.cfg`.

---

## Repository Server List (pytdx/config/hosts.py)

### Standard Quote Servers (Port 7709)

| Broker | IP Address | Port |
|--------|------------|------|
| 长城国瑞电信1 | 218.85.139.19 | 7709 |
| 长城国瑞电信2 | 218.85.139.20 | 7709 |
| 上证云成都电信一 | 218.6.170.47 | 7709 |
| 上证云北京联通一 | 123.125.108.14 | 7709 |
| 上海电信主站Z1 | 180.153.18.170 | 7709 |
| 上海电信主站Z2 | 180.153.18.171 | 7709 |
| 北京联通主站Z1 | 202.108.253.130 | 7709 |
| 北京联通主站Z2 | 202.108.253.131 | 7709 |
| 杭州电信主站J1 | 60.191.117.167 | 7709 |
| 深圳电信主站Z1 | 14.17.75.71 | 7709 |
| 招商证券深圳行情 | 119.147.212.81 | 7709 |
| 华泰证券(南京电信) | 221.231.141.60 | 7709 |
| 华泰证券(上海电信) | 101.227.73.20 | 7709 |
| 广发证券 | 119.29.19.242 | 7709 |
| 国泰君安 | 113.105.92.100 | 7709 |
| 国信证券 | 182.131.3.252 | 7709 |
| 海通证券 | 123.125.108.90 | 7709 |
| ... | ... | ... |

Total: ~100+ servers from various brokers.

---

## ZSZQ PC Software Server List (connect.cfg)

### HQHOST - Standard Quote Servers (Port 7709)

| Name | IP Address | Port | Notes |
|------|------------|------|-------|
| 招商上海云1 | 39.108.28.83 | 7709 | Primary (matches screenshot) |
| 招商上海云2 | 109.244.75.133 | 7709 | |
| 招商北京云1 | 39.105.251.234 | 7709 | |
| 招商北京云2 | 120.53.204.206 | 7709 | |
| 招商北京云3 | 109.244.7.169 | 7709 | |
| 招商广州云1 | 111.230.189.225 | 7709 | |
| 招商广州云2 | 106.53.111.126 | 443 | SSL port |
| 招商上海云 | 47.100.132.162 | 7709 | Matches your screenshot |
| 招商上海云2 | 43.145.21.43 | 7709 | |
| 招商南京云 | 116.57.224.5 | 7709 | |
| 招商大连电信 | 183.62.101.52 | 7709 | Area=1 |
| 招商深圳联通 | 58.251.16.180 | 7709 | Area=2 |
| 招商北京云IPV6 | 2402:4e00:1201:c700:0:9255:264d:75c | 7709 | IPv6 |
| 招商广州云IPV6 | 2402:4e00:1012:de00:0:9255:2170:e012 | 7709 | IPv6 |

### INFOHOST - Info/News Servers (Port 7711)

| Name | IP Address | Port |
|------|------------|------|
| 招商上海云1 | 39.108.28.83 | 7711 |
| 招商北京云1 | 39.105.251.234 | 7711 |
| 招商北京云2 | 120.53.204.206 | 7711 |
| 招商广州云1 | 111.230.189.225 | 7711 |
| 招商广州云2 | 106.53.111.126 | 80 |
| 招商南京云 | 116.57.224.5 | 7711 |
| 招商广州云IPV6 | 2402:4e00:1012:de00:0:9255:2170:e012 | 7711 |
| 招商北京云IPV6 | 2402:4e00:1201:c700:0:9255:264d:75c | 7711 |

### DSHOST - Extended Market Servers (Port 7727)

| Name | IP Address | Port | Region |
|------|------------|------|--------|
| 深圳云1 | 193.112.226.233 | 7727 | Shenzhen |
| 深圳云1 | 47.112.210.90 | 7727 | Shenzhen |
| 上海云1 | 101.132.165.164 | 7727 | Shanghai |
| 上海云2 | 118.25.33.72 | 7727 | Shanghai |
| 北京云1 | 8.141.17.79 | 7727 | Beijing |
| 北京云2 | 43.144.168.241 | 7727 | Beijing |

### DSHOST_EXTERN - Extended Market Backup (Port 7727)

| Name | IP Address | Port |
|------|------------|------|
| 深圳云2 | 134.175.239.244 | 7727 |
| 深圳云2 | 47.107.229.33 | 7727 |
| 上海云3 | 47.102.204.129 | 7727 |

---

## Key Differences

### 1. Newer Cloud Infrastructure
The ZSZQ software uses **modern cloud servers** (2023-2024):
- Alibaba Cloud (47.x, 39.x, 120.x ranges)
- Tencent Cloud (106.x, 111.x, 101.x ranges)
- IPv6 support

The repo list has **older servers**, many likely outdated.

### 2. Port Variations
| Service | Standard Port | Notes |
|---------|--------------|-------|
| Quote | 7709 | Standard TDX quote port |
| Info | 7711 | News/F10 data |
| Extended | 7727 | Futures/options |
| SSL | 443 | Encrypted quote connection |
| Web | 80 | HTTP fallback |

### 3. From Screenshot Validation
Your screenshot shows:
- **行情主站** (Quote Master): 47.100.132.162:7709 ✓ Matches Host08
- **资讯主站** (Info Master): 39.108.28.83:7711 ✓ Matches INFOHOST
- **扩展市场行情** (Extended Market): 101.132.165.164:7727 ✓ Matches DSHOST

---

## Recommended Updates to Repo

### New Servers to Add (from ZSZQ)

```python
# ZSZQ Cloud Servers (招商证券 - 2024)
zszq_hosts = [
    ("招商上海云1", "39.108.28.83", 7709),
    ("招商上海云2", "109.244.75.133", 7709),
    ("招商北京云1", "39.105.251.234", 7709),
    ("招商北京云2", "120.53.204.206", 7709),
    ("招商北京云3", "109.244.7.169", 7709),
    ("招商广州云1", "111.230.189.225", 7709),
    ("招商上海云", "47.100.132.162", 7709),
    ("招商上海云2", "43.145.21.43", 7709),
    ("招商南京云", "116.57.224.5", 7709),
]

# Extended Market Servers (DSHOST)
dshost_exhq = [
    ("扩展行情-深圳云1", "193.112.226.233", 7727),
    ("扩展行情-深圳云2", "47.112.210.90", 7727),
    ("扩展行情-上海云1", "101.132.165.164", 7727),
    ("扩展行情-上海云2", "118.25.33.72", 7727),
    ("扩展行情-北京云1", "8.141.17.79", 7727),
    ("扩展行情-北京云2", "43.144.168.241", 7727),
]
```

---

## How to Extract from Other TDX Software

Any TDX-based software stores servers in `connect.cfg`:

```bash
# Find the config file
ls /mnt/c/*/connect.cfg

# Extract IP:Port pairs
grep -E "^IPAddress|^Port" /mnt/c/zd_zsone/connect.cfg

# Decode Chinese names (GBK encoding)
iconv -f GBK -f UTF-8 /mnt/c/zd_zsone/connect.cfg > decoded.cfg
```

---

## Verification

Test if servers are alive:

```python
from pytdx.hq import TdxHq_API

api = TdxHq_API()

# Test new ZSZQ server
if api.connect('47.100.132.162', 7709):
    quotes = api.get_security_quotes([(0, '000001')])
    print(f"Server alive: {quotes}")
    api.disconnect()
```

---

## Files in ZSZQ Directory

| File | Purpose |
|------|---------|
| `connect.cfg` | Server list, user settings |
| `vipdoc/` | Local market data cache (.day, .lc1, .lc5 files) |
| `T0001/`, `T0002/` | User configuration, custom blocks |
| `areas.dat` | Regional server mapping |
| `dsmarket.dat` | Extended market configuration |
