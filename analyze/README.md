# TDX Protocol Analyzer / 通达信协议分析器

Python 工具集，用于分析 TDX (通达信) 协议的网络抓包文件。

## 安装依赖

```bash
pip install scapy
```

## 快速开始

### 1. 基本分析

```bash
python tdx_pcap_analyzer.py capture.pcapng
```

### 2. 只显示摘要

```bash
python tdx_pcap_analyzer.py capture.pcapng --summary
```

输出示例:
```
======================================================================
TDX PCAP 分析摘要
======================================================================
文件: capture.pcapng
端口: 7709
总数据包: 156
  - 请求: 78
  - 响应: 78
已知命令: 142
未知命令: 14

命令分布:
  [✓] GetSecurityQuotes            :   45
  [✓] GetSecurityBars              :   32
  [?] Unknown(0x1234)              :   10
  ...

未知命令列表:
  0x1234 : 6 次
  0x5678 : 4 次
```

### 3. 分析未知包

```bash
python tdx_pcap_analyzer.py capture.pcapng --unknown
```

### 4. 导出未知包到 JSON

```bash
python tdx_pcap_analyzer.py capture.pcapng --export unknown_packets.json
```

### 5. 显示 hex dump

```bash
python tdx_pcap_analyzer.py capture.pcapng --hex
```

## 作为 Python 模块使用

```python
from analyze import TdxPcapAnalyzer

# 创建分析器
analyzer = TdxPcapAnalyzer("capture.pcapng", port=7709)
analyzer.load_pcap()

# 打印摘要
analyzer.print_summary()

# 获取未知包
from analyze import TdxCommandRegistry

unknown = [p for p in analyzer.packets
           if p.cmd and not TdxCommandRegistry.is_known(p.cmd)]

for pkt in unknown:
    print(f"Unknown cmd: 0x{pkt.cmd:04x}")
    print(f"Payload: {pkt.payload[:32].hex()}")
```

## 抓包指南

### 使用 tcpdump

```bash
sudo tcpdump -i eth0 -w tdx_capture.pcapng 'port 7709'
```

### 使用 Wireshark/tshark

```bash
tshark -i eth0 -f "port 7709" -w tdx_capture.pcapng
```

### 使用 ZSZQ 软件时捕获

1. 开始抓包
2. 打开 ZSZQ 软件并登录
3. 执行以下操作:
   - 查看股票列表
   - 切换 K 线图
   - 查看实时行情
   - 刷新数据
4. 停止抓包

## 已知命令

| 命令 | 名称 | 描述 |
|------|------|------|
| 0x0201 | SetupCmd1 | 初始化命令1 |
| 0x0202 | SetupCmd2 | 初始化命令2 |
| 0x0302 | SetupCmd3 | 初始化命令3 |
| 0x0463 | GetSecurityQuotes | 获取实时行情 |
| 0x0864 | GetSecurityBars | 获取K线数据 |
| 0x056b | GetTransactionData | 获取逐笔成交 |
| 0x066e | GetSecurityList | 获取股票列表 |
| 0x016e | GetSecurityCount | 获取股票数量 |
| 0x056d | GetMinuteTimeData | 获取分时数据 |
| 0x1c76 | GetFinanceInfo | 获取财务信息 |

## 扩展命令注册表

要添加新的已知命令，编辑 `tdx_pcap_analyzer.py` 中的 `TdxCommandRegistry` 类:

```python
COMMANDS = {
    ...
    0x1234: {"name": "NewCommand", "category": "custom", "desc": "新命令"},
}
```

## 项目结构

```
analyze/
├── __init__.py           # 模块导出
├── tdx_pcap_analyzer.py  # 主分析器
└── README.md            # 本文档
```

## 分析未知包的流程

1. **抓包**: 使用 Wireshark 或 tcpdump 捕获 TDX 通信
2. **分析**: 运行 `tdx_pcap_analyzer.py --unknown` 识别未知包
3. **观察**: 记录未知包出现时的操作（如查看K线、获取列表等）
4. **推测**: 根据包大小、请求/响应模式、payload 内容推测功能
5. **验证**: 修改解析器，添加新命令，重新分析验证
6. **文档**: 更新命令注册表，记录协议细节

## 注意事项

- 需要 root/admin 权限进行网络抓包
- 某些响应包可能是 zlib 压缩的，需要解压缩分析
- 协议可能会随软件版本更新而变化
- 尊重隐私和版权，仅用于学习和研究目的
