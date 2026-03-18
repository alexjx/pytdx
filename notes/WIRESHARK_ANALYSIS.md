# Wireshark 协议分析指南 - TDX Protocol

## 1. Wireshark 抓包设置

### 过滤器设置

```
# 只捕获 TDX 相关端口
tcp.port == 7709 || tcp.port == 7727 || tcp.port == 7711

# 或指定 IP
tcp.host == 47.100.132.162

# 组合条件
tcp.port == 7709 && tcp.payload
```

### 捕获选项
- Interface: 选择你的网卡（以太网或WiFi）
- Capture filter: `port 7709 or port 7727 or port 7711`
- 开始捕获前先打开 ZSZQ 软件

---

## 2. 命令行工具 Tshark

### 基础用法

```bash
# 实时捕获并显示
tshark -i eth0 -f "port 7709"

# 捕获到文件
tshark -i eth0 -f "port 7709" -w tdx_capture.pcapng

# 读取 pcap 文件
tshark -r tdx_capture.pcapng

# 只显示特定字段
tshark -r tdx_capture.pcapng -T fields -e frame.number -e ip.src -e ip.dst -e tcp.payload
```

### 提取 TCP Payload

```bash
# 方法1: 导出 payload 到文本
tshark -r tdx_capture.pcapng \
  -Y "tcp.payload" \
  -T fields \
  -e ip.src \
  -e ip.dst \
  -e tcp.srcport \
  -e tcp.dstport \
  -e tcp.payload \
  > tdx_payload.txt

# 方法2: 导出原始二进制数据
tshark -r tdx_capture.pcapng \
  -Y "tcp.payload" \
  -T fields \
  -e tcp.payload \
  | xxd -r -p > tdx_raw.bin

# 方法3: 按流导出
tshark -r tdx_capture.pcapng \
  -q \
  -z follow,tcp,hex,0  # 0 是流编号
```

### 提取特定数据包

```bash
# 只提取客户端发送的数据（帧长度 < 100 通常是请求）
tshark -r tdx_capture.pcapng \
  -Y "frame.len < 100 && ip.src == 192.168.1.100" \
  -T fields \
  -e tcp.payload

# 只提取服务器响应（帧长度 > 100 通常是响应）
tshark -r tdx_capture.pcapng \
  -Y "frame.len > 200 && ip.dst == 192.168.1.100" \
  -T fields \
  -e tcp.payload
```

---

## 3. Lua 解析器开发

### 创建 TDX 协议解析器

创建文件 `~/.local/lib/wireshark/plugins/tdx_proto.lua`:

```lua
-- TDX Protocol Dissector
local tdx_proto = Proto("tdx", "TDX Protocol")

-- 定义字段
local f_magic = ProtoField.uint16("tdx.magic", "Magic", base.HEX)
local f_cmd = ProtoField.uint16("tdx.cmd", "Command", base.HEX)
local f_len = ProtoField.uint32("tdx.length", "Data Length", base.DEC)
local f_data = ProtoField.bytes("tdx.data", "Data")
local f_market = ProtoField.uint8("tdx.market", "Market", base.DEC)
local f_code = ProtoField.string("tdx.code", "Code")

tdx_proto.fields = {f_magic, f_cmd, f_len, f_data, f_market, f_code}

-- 命令类型映射
local cmd_types = {
    [0x0c02] = "Setup Cmd 1",
    [0x0c03] = "Setup Cmd 2/3",
    [0x0c01] = "Quote Request",
    [0x10c] = "KLine Request",
    [0x10d] = "Transaction Request",
}

-- 解析函数
function tdx_proto.dissector(buffer, pinfo, tree)
    local length = buffer:len()
    if length < 16 then return end

    pinfo.cols.protocol = tdx_proto.name

    local subtree = tree:add(tdx_proto, buffer(), "TDX Protocol Data")

    -- 解析头部 (16 bytes)
    local magic = buffer(0, 2):uint()
    local cmd = buffer(2, 2):uint()
    local data_len = buffer(4, 4):le_uint()

    subtree:add(f_magic, buffer(0, 2))

    local cmd_desc = cmd_types[cmd] or string.format("Unknown (0x%04x)", cmd)
    subtree:add(f_cmd, buffer(2, 2)):append_text(" (" .. cmd_desc .. ")")
    subtree:add(f_len, buffer(4, 4))

    -- 如果有数据
    if length > 16 then
        subtree:add(f_data, buffer(16, length - 16))

        -- 尝试解析股票代码
        if cmd == 0x0c01 or cmd == 0x10c then
            if length >= 23 then
                local market = buffer(16, 1):uint()
                local code = buffer(17, 6):string()
                subtree:add(f_market, buffer(16, 1))
                subtree:add(f_code, buffer(17, 6))
            end
        end
    end

    -- 更新信息列
    pinfo.cols.info = cmd_desc
end

-- 注册到 TCP 端口 7709
local tcp_table = DissectorTable.get("tcp.port")
tcp_table:add(7709, tdx_proto)
tcp_table:add(7727, tdx_proto)
tcp_table:add(7711, tdx_proto)
```

### Lua 解析器高级版本

```lua
-- tdx_advanced.lua - 更完整的 TDX 解析器

local tdx = Proto("tdx_adv", "TDX Advanced")

-- 创建字段
local fields = {
    -- 头部
    header_magic = ProtoField.uint16("tdx.header.magic", "Magic", base.HEX),
    header_cmd = ProtoField.uint16("tdx.header.cmd", "Command Type", base.HEX),
    header_len = ProtoField.uint32("tdx.header.length", "Payload Length"),
    header_reserved = ProtoField.bytes("tdx.header.reserved", "Reserved"),

    -- 请求特定
    req_market = ProtoField.uint8("tdx.req.market", "Market", base.DEC, {
        [0] = "Shenzhen",
        [1] = "Shanghai"
    }),
    req_code = ProtoField.string("tdx.req.code", "Stock Code"),
    req_category = ProtoField.uint16("tdx.req.category", "KLine Category"),
    req_start = ProtoField.uint32("tdx.req.start", "Start Index"),
    req_count = ProtoField.uint16("tdx.req.count", "Count"),

    -- 响应特定
    rsp_count = ProtoField.uint16("tdx.rsp.count", "Record Count"),
    rsp_data = ProtoField.bytes("tdx.rsp.data", "Compressed Data"),
}

tdx.fields = fields

-- 命令名称
function get_cmd_name(cmd)
    local names = {
        [0x0201] = "Setup 1",
        [0x0202] = "Setup 2",
        [0x0302] = "Setup 3",
        [0x0463] = "Get Quotes",
        [0x0864] = "Get KLine",
        [0x056b] = "Get Transactions",
    }
    return names[cmd] or string.format("Cmd 0x%04x", cmd)
end

function tdx.dissector(buf, pinfo, root)
    local len = buf:len()
    if len < 16 then return end

    pinfo.cols.protocol = "TDX"
    local tree = root:add(tdx, buf())

    -- 解析头部
    local magic = buf(0, 2):uint()
    local cmd_hi = buf(2, 1):uint()
    local cmd_lo = buf(3, 1):uint()
    local cmd = buf(2, 2):uint()
    local payload_len = buf(4, 4):le_uint()

    local header_tree = tree:add(buf(0, 16), "TDX Header")
    header_tree:add(fields.header_magic, buf(0, 2))
    header_tree:add(fields.header_cmd, buf(2, 2)):append_text(" (" .. get_cmd_name(cmd) .. ")")
    header_tree:add(fields.header_len, buf(4, 4))
    header_tree:add(fields.header_reserved, buf(8, 8))

    -- 更新信息列
    pinfo.cols.info = get_cmd_name(cmd)

    -- 解析 payload
    if len > 16 then
        local payload = tree:add(buf(16, len-16), "Payload (" .. (len-16) .. " bytes)")

        -- 根据命令类型解析
        if cmd == 0x0864 and len >= 28 then  -- Get KLine
            payload:add(fields.req_market, buf(16, 1))
            payload:add(fields.req_code, buf(17, 6))
            payload:add(fields.req_category, buf(23, 2))
            payload:add(fields.req_start, buf(27, 4))
            payload:add(fields.req_count, buf(31, 2))
        end
    end
end

-- 注册
DissectorTable.get("tcp.port"):add(7709, tdx)
```

---

## 4. Python 自动化解析

### 从 pcap 提取并解析

```python
#!/usr/bin/env python3
"""
TDX PCAP 解析器
依赖: pip install scapy pyshark
"""

import pyshark
import struct
from typing import List, Dict

class TdxPcapParser:
    def __init__(self, pcap_file: str):
        self.pcap_file = pcap_file
        self.packets = []

    def extract_conversations(self) -> List[Dict]:
        """提取 TCP 会话"""
        cap = pyshark.FileCapture(
            self.pcap_file,
            display_filter="tcp.port == 7709 && tcp.payload"
        )

        conversations = []
        for pkt in cap:
            if hasattr(pkt, 'tcp') and hasattr(pkt.tcp, 'payload'):
                payload = bytes.fromhex(pkt.tcp.payload.replace(':', ''))

                conv = {
                    'timestamp': float(pkt.sniff_timestamp),
                    'src_ip': pkt.ip.src,
                    'dst_ip': pkt.ip.dst,
                    'src_port': int(pkt.tcp.srcport),
                    'dst_port': int(pkt.tcp.dstport),
                    'payload': payload,
                    'payload_len': len(payload),
                    'is_request': len(payload) < 100,  # 请求通常较短
                }
                conversations.append(conv)

        cap.close()
        return conversations

    def parse_tdx_header(self, payload: bytes) -> Dict:
        """解析 TDX 头部"""
        if len(payload) < 16:
            return None

        return {
            'magic': payload[0:2].hex(),
            'cmd': payload[2:4].hex(),
            'cmd_int': struct.unpack('<H', payload[2:4])[0],
            'data_len': struct.unpack('<I', payload[4:8])[0],
            'total_len': len(payload)
        }

    def parse_quote_request(self, payload: bytes) -> Dict:
        """解析行情请求"""
        if len(payload) < 23:
            return None

        num_stocks = struct.unpack('<H', payload[12:14])[0]
        stocks = []

        pos = 16
        for i in range(num_stocks):
            if pos + 7 > len(payload):
                break
            market = payload[pos]
            code = payload[pos+1:pos+7].decode('utf-8', errors='ignore').strip('\x00')
            stocks.append({'market': market, 'code': code})
            pos += 7

        return {'num_stocks': num_stocks, 'stocks': stocks}

    def analyze(self):
        """完整分析"""
        conversations = self.extract_conversations()

        print(f"总共 {len(conversations)} 个数据包\n")

        for i, conv in enumerate(conversations[:20]):  # 显示前20个
            header = self.parse_tdx_header(conv['payload'])

            direction = "→ 请求" if conv['is_request'] else "← 响应"
            print(f"[{i+1}] {direction} {conv['src_ip']}:{conv['src_port']} -> "
                  f"{conv['dst_ip']}:{conv['dst_port']}")

            if header:
                print(f"    命令: 0x{header['cmd']} (Magic: 0x{header['magic']})")
                print(f"    数据长度: {header['data_len']} bytes")

                # 如果是行情请求，解析股票代码
                if header['cmd_int'] == 0x6302:  # Quote request
                    req = self.parse_quote_request(conv['payload'])
                    if req:
                        print(f"    请求股票数: {req['num_stocks']}")
                        for s in req['stocks']:
                            market_name = "深圳" if s['market'] == 0 else "上海"
                            print(f"      - {market_name} {s['code']}")

            print(f"    Payload (hex): {conv['payload'][:32].hex()}...")
            print()


# 使用示例
if __name__ == "__main__":
    parser = TdxPcapParser("tdx_capture.pcapng")
    parser.analyze()
```

---

## 5. 完整的分析流程

### 步骤1: 抓包

```bash
# 开始抓包
tshark -i eth0 -f "port 7709" -w tdx_session.pcapng

# 同时运行 ZSZQ 软件执行以下操作:
# 1. 连接行情服务器
# 2. 查看几只股票
# 3. 切换K线图
# 4. 查看分时图
# 然后停止抓包 (Ctrl+C)
```

### 步骤2: 分析会话

```bash
# 查看 TCP 流列表
tshark -r tdx_session.pcapng -q -z conv,tcp

# 导出特定流
tshark -r tdx_session.pcapng -q -z follow,tcp,hex,0 > stream_0.hex
```

### 步骤3: Python 深度分析

```python
#!/usr/bin/env python3
import struct
from scapy.all import *

# 读取 pcap
packets = rdpcap("tdx_session.pcapng")

# 提取请求-响应对
for i, pkt in enumerate(packets):
    if TCP in pkt and Raw in pkt:
        payload = bytes(pkt[Raw])

        # 简单的启发式判断
        if len(payload) >= 16:
            cmd = struct.unpack('<H', payload[2:4])[0]
            print(f"Packet {i}: Cmd=0x{cmd:04x}, Len={len(payload)}")

            # 打印 hex dump
            print(f"  Hex: {payload[:40].hex()}")
```

### 步骤4: 协议逆向

```python
# 对比已知请求和响应，推断协议结构

# 例如，已知请求 000001 的行情:
known_request = bytes.fromhex(
    "0c0263201d001d000e530500000000000200"
    "00303030303031"  # "000001"
    "0001"            # market=0, ?
)

# 分析响应
# 响应通常是 zlib 压缩的，需要解压
import zlib

response = bytes.fromhex("...")  # 抓包的响应
# 前16字节是头部，后面是压缩数据
compressed = response[16:]
decompressed = zlib.decompress(compressed)
print(f"解压后: {decompressed.hex()}")
```

---

## 6. 推荐的工具链

| 工具 | 用途 | 命令 |
|------|------|------|
| **Wireshark** | GUI 分析 | `wireshark tdx.pcapng` |
| **tshark** | CLI 提取 | `tshark -r file.pcapng -T fields -e tcp.payload` |
| **tcpdump** | 快速抓包 | `tcpdump -i eth0 port 7709 -w file.pcap` |
| **scapy** | Python 解析 | `packets = rdpcap("file.pcap")` |
| **pyshark** | 高级解析 | `pyshark.FileCapture("file.pcap")` |
| **xxd** | Hex 查看 | `xxd file.bin | head -20` |

---

## 7. 快速参考

### 常用 tshark 命令

```bash
# 提取所有 payload 并保存
tshark -r capture.pcapng -T fields -e tcp.payload | tr -d '\n' | xxd -r -p > all_payload.bin

# 统计包大小分布
tshark -r capture.pcapng -Y "tcp.port == 7709" -T fields -e frame.len | sort | uniq -c | sort -rn

# 提取特定大小的包 (如请求包)
tshark -r capture.pcapng -Y "frame.len == 45" -T fields -e tcp.payload

# 按时间戳和 payload 导出
tshark -r capture.pcapng -t e -Y "tcp.payload" -T fields -e frame.time_relative -e tcp.payload
```

### Lua 解析器调试

```lua
-- 在 Lua 中添加调试输出
if payload_len > 0 then
    -- 使用 tree:add 的文本描述来调试
    tree:add(buf(16, 1), "Debug: First byte = " .. buf(16, 1):uint())
end
```

Wireshark 控制台: `Analyze` -> `Reload Lua Plugins` (Ctrl+Shift+L)
