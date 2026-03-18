#!/usr/bin/env python3
"""
TDX Protocol PCAP Analyzer
分析通达信协议的数据包，识别已知和未知的数据包类型

Usage:
    python tdx_pcap_analyzer.py <pcap_file> [options]

Options:
    --port PORT     指定端口 (默认: 7709)
    --summary       只显示摘要
    --unknown       只显示未知包
    --export FILE   导出未知包到文件
    --hex           显示 hex dump
"""

import sys
import struct
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import json

try:
    from scapy.all import rdpcap, TCP, Raw, IP
except ImportError:
    print("Error: scapy not installed. Run: pip install scapy")
    sys.exit(1)


@dataclass
class TdxPacket:
    """TDX 数据包结构"""
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    payload: bytes
    is_request: bool

    # 解析后的字段
    magic: Optional[int] = None
    cmd: Optional[int] = None
    data_len: Optional[int] = None
    cmd_name: str = "Unknown"
    parsed_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.parsed_data is None:
            self.parsed_data = {}


class TdxCommandRegistry:
    """TDX 命令注册表 - 已知的命令类型

    命令字节位于数据包偏移 2-3 位置 (小端序)
    标准行情 API (端口 7709): Byte 0 = 0x0c
    扩展行情 API (端口 7727): Byte 0 = 0x01
    """

    COMMANDS = {
        # ========== Setup 命令 ==========
        0x9318: {"name": "SetupCmd1", "category": "setup", "desc": "初始化命令1", "api": "std"},
        0x9418: {"name": "SetupCmd2", "category": "setup", "desc": "初始化命令2", "api": "std"},
        0x9918: {"name": "SetupCmd3", "category": "setup", "desc": "初始化命令3", "api": "std"},

        # ========== 行情数据 ==========
        0x6320: {"name": "GetSecurityQuotes", "category": "quote", "desc": "获取股票实时行情", "api": "std"},
        0x6408: {"name": "GetSecurityBars", "category": "kline", "desc": "获取K线数据", "api": "std"},
        0x6a10: {"name": "GetIndexBars", "category": "kline", "desc": "获取指数K线", "api": "std"},

        # ========== 成交数据 ==========
        0x0108: {"name": "GetTransactionData", "category": "transaction", "desc": "获取逐笔成交", "api": "std"},
        0x0130: {"name": "GetHistoryTransactionData", "category": "transaction", "desc": "获取历史逐笔成交", "api": "std"},

        # ========== 分时数据 ==========
        0x0008: {"name": "GetMinuteTimeData", "category": "minute", "desc": "获取分时数据", "api": "std"},
        0x0030: {"name": "GetHistoryMinuteTimeData", "category": "minute", "desc": "获取历史分时数据", "api": "std"},

        # ========== 股票列表 ==========
        0x6418: {"name": "GetSecurityList", "category": "list", "desc": "获取股票列表", "api": "std"},
        0x6c18: {"name": "GetSecurityCount", "category": "count", "desc": "获取股票数量", "api": "std"},

        # ========== 财务/公司信息 ==========
        0x7618: {"name": "GetFinanceInfo/XdXrInfo", "category": "finance", "desc": "获取财务信息/除权除息", "api": "std"},
        0x9b10: {"name": "GetCompanyInfoCategory", "category": "company", "desc": "获取公司信息目录", "api": "std"},
        0x9c10: {"name": "GetCompanyInfoContent", "category": "company", "desc": "获取公司信息内容", "api": "std"},

        # ========== 板块信息 ==========
        0x6918: {"name": "GetBlockInfo", "category": "block", "desc": "获取板块信息", "api": "std"},
        0x6a18: {"name": "GetBlockInfoMeta", "category": "block", "desc": "获取板块信息元数据", "api": "std"},

        # ========== 文件下载 ==========
        0x0034: {"name": "GetReportFile", "category": "file", "desc": "下载报告文件", "api": "std"},

        # ========== 扩展行情 API (端口 7727) ==========
        0x6548: {"name": "ExSetupCmd1", "category": "ex_setup", "desc": "扩展行情初始化", "api": "ex"},
        0x6948: {"name": "ExGetMarkets", "category": "ex_list", "desc": "获取扩展市场列表", "api": "ex"},
        0x6648: {"name": "ExGetInstrumentCount", "category": "ex_count", "desc": "获取扩展行情合约数量", "api": "ex"},
        0x6748: {"name": "ExGetInstrumentInfo", "category": "ex_list", "desc": "获取扩展行情合约信息", "api": "ex"},
        0x0208: {"name": "ExGetInstrumentQuote", "category": "ex_quote", "desc": "获取扩展行情合约报价", "api": "ex"},
        0x6a08: {"name": "ExGetInstrumentBars", "category": "ex_kline", "desc": "获取扩展行情K线", "api": "ex"},
        0x0b06: {"name": "ExGetInstrumentQuoteList", "category": "ex_quote", "desc": "获取扩展行情合约报价列表", "api": "ex"},
        # 注意: 以下扩展行情命令与标准API命令字节相同，需要通过端口区分
        # 0x0008: ExGetMinuteTimeData / ExGetTransactionData (端口 7727)
        # 0x0030: ExGetHistoryMinuteTimeData (端口 7727)
        # 0x0624: ExGetHistoryTransactionData (端口 7727)
        0x9238: {"name": "ExGetHistoryInstrumentBarsRange", "category": "ex_kline", "desc": "获取扩展行情历史K线范围", "api": "ex"},
    }

    # 响应包的 magic (前2字节)
    RESPONSE_MAGIC = {
        0xcb74: "Standard Response",
        0xcb75: "Standard Response Alt",
        0x0074: "Short Response",
    }

    @classmethod
    def get_command_name(cls, cmd: int) -> str:
        if cmd in cls.COMMANDS:
            return cls.COMMANDS[cmd]["name"]
        return f"Unknown(0x{cmd:04x})"

    @classmethod
    def get_command_category(cls, cmd: int) -> str:
        if cmd in cls.COMMANDS:
            return cls.COMMANDS[cmd]["category"]
        return "unknown"

    @classmethod
    def is_known(cls, cmd: int) -> bool:
        return cmd in cls.COMMANDS


class TdxPacketParser:
    """TDX 数据包解析器"""

    def __init__(self):
        self.registry = TdxCommandRegistry()

    def parse_header(self, payload: bytes) -> Optional[Dict]:
        """解析 TDX 头部 (16 bytes)"""
        if len(payload) < 16:
            return None

        # 小端序解析
        magic = struct.unpack('<H', payload[0:2])[0]
        cmd = struct.unpack('<H', payload[2:4])[0]
        data_len = struct.unpack('<I', payload[4:8])[0]

        return {
            'magic': magic,
            'cmd': cmd,
            'data_len': data_len,
            'raw_header': payload[:16].hex()
        }

    def parse_quote_request(self, payload: bytes) -> Dict:
        """解析行情请求"""
        result = {'type': 'quote_request'}

        if len(payload) < 20:
            return result

        try:
            # 股票数量在偏移 12-14
            num_stocks = struct.unpack('<H', payload[12:14])[0]
            result['num_stocks'] = num_stocks
            result['stocks'] = []

            # 股票列表从偏移 16 开始，每个 7 bytes (1 byte market + 6 bytes code)
            pos = 16
            for i in range(min(num_stocks, 50)):  # 最多解析50只
                if pos + 7 > len(payload):
                    break

                market = payload[pos]
                code = payload[pos+1:pos+7].decode('utf-8', errors='ignore').strip('\x00')

                result['stocks'].append({
                    'market': market,
                    'market_name': '深圳' if market == 0 else '上海' if market == 1 else f'未知({market})',
                    'code': code
                })
                pos += 7

        except Exception as e:
            result['error'] = str(e)

        return result

    def parse_kline_request(self, payload: bytes) -> Dict:
        """解析K线请求"""
        result = {'type': 'kline_request'}

        if len(payload) < 28:
            return result

        try:
            result['market'] = payload[16]
            result['code'] = payload[17:23].decode('utf-8', errors='ignore').strip('\x00')
            result['category'] = struct.unpack('<H', payload[23:25])[0]
            result['start'] = struct.unpack('<I', payload[27:31])[0]
            result['count'] = struct.unpack('<H', payload[31:33])[0]

            # K线类型映射
            kline_types = {
                0: '5分钟', 1: '15分钟', 2: '30分钟', 3: '1小时',
                4: '日线', 5: '周线', 6: '月线',
                7: '1分钟(扩展)', 8: '1分钟', 9: '日线',
                10: '季线', 11: '年线'
            }
            result['category_name'] = kline_types.get(result['category'], f"未知({result['category']})")

        except Exception as e:
            result['error'] = str(e)

        return result

    def parse_response(self, payload: bytes, cmd: int) -> Dict:
        """解析响应数据"""
        result = {'type': 'response', 'cmd': f"0x{cmd:04x}"}

        # 响应数据通常以股票数量开始 (偏移 2-4)
        if len(payload) > 4:
            try:
                num_records = struct.unpack('<H', payload[2:4])[0]
                result['num_records'] = num_records
            except:
                pass

        return result

    def parse(self, packet: TdxPacket) -> TdxPacket:
        """解析完整数据包"""
        header = self.parse_header(packet.payload)

        if header:
            packet.magic = header['magic']
            packet.cmd = header['cmd']
            packet.data_len = header['data_len']
            packet.cmd_name = self.registry.get_command_name(packet.cmd)

            # 根据命令类型深度解析
            if packet.is_request:
                if packet.cmd == 0x0463:
                    packet.parsed_data = self.parse_quote_request(packet.payload)
                elif packet.cmd == 0x0864:
                    packet.parsed_data = self.parse_kline_request(packet.payload)
            else:
                packet.parsed_data = self.parse_response(packet.payload, packet.cmd)

        return packet


class TdxPcapAnalyzer:
    """TDX PCAP 分析器主类"""

    def __init__(self, pcap_file: str, port: int = 7709):
        self.pcap_file = pcap_file
        self.port = port
        self.parser = TdxPacketParser()
        self.packets: List[TdxPacket] = []
        self.stats = {
            'total': 0,
            'known': 0,
            'unknown': 0,
            'requests': 0,
            'responses': 0
        }

    def load_pcap(self):
        """加载 pcap 文件"""
        print(f"[INFO] 正在加载 {self.pcap_file}...")

        try:
            packets = rdpcap(self.pcap_file)
        except Exception as e:
            print(f"[ERROR] 无法读取 pcap 文件: {e}")
            sys.exit(1)

        for pkt in packets:
            if not pkt.haslayer(TCP) or not pkt.haslayer(Raw):
                continue

            tcp = pkt[TCP]
            payload = bytes(tcp.payload)

            # 只处理指定端口的数据
            if tcp.sport != self.port and tcp.dport != self.port:
                continue

            # 忽略空包
            if len(payload) < 16:
                continue

            # 判断请求/响应
            is_request = tcp.dport == self.port

            # 创建 TdxPacket
            tdx_pkt = TdxPacket(
                timestamp=float(pkt.time),
                src_ip=pkt[IP].src if pkt.haslayer(IP) else "0.0.0.0",
                dst_ip=pkt[IP].dst if pkt.haslayer(IP) else "0.0.0.0",
                src_port=tcp.sport,
                dst_port=tcp.dport,
                payload=payload,
                is_request=is_request
            )

            # 解析数据包
            self.parser.parse(tdx_pkt)
            self.packets.append(tdx_pkt)

        self._update_stats()
        print(f"[INFO] 加载完成: {len(self.packets)} 个数据包")

    def _update_stats(self):
        """更新统计信息"""
        self.stats['total'] = len(self.packets)
        self.stats['requests'] = sum(1 for p in self.packets if p.is_request)
        self.stats['responses'] = sum(1 for p in self.packets if not p.is_request)
        self.stats['known'] = sum(1 for p in self.packets if p.cmd and TdxCommandRegistry.is_known(p.cmd))
        self.stats['unknown'] = self.stats['total'] - self.stats['known']

    def print_summary(self):
        """打印摘要信息"""
        print("\n" + "=" * 70)
        print("TDX PCAP 分析摘要")
        print("=" * 70)
        print(f"文件: {self.pcap_file}")
        print(f"端口: {self.port}")
        print(f"总数据包: {self.stats['total']}")
        print(f"  - 请求: {self.stats['requests']}")
        print(f"  - 响应: {self.stats['responses']}")
        print(f"已知命令: {self.stats['known']}")
        print(f"未知命令: {self.stats['unknown']}")

        # 命令分布
        print("\n命令分布:")
        cmd_counter = Counter([p.cmd_name for p in self.packets if p.cmd])
        for cmd_name, count in cmd_counter.most_common():
            known = "✓" if "Unknown" not in cmd_name else "?"
            print(f"  [{known}] {cmd_name:30s} : {count:4d}")

        # 未知命令详情
        unknown_cmds = [p.cmd for p in self.packets if p.cmd and not TdxCommandRegistry.is_known(p.cmd)]
        if unknown_cmds:
            print("\n未知命令列表:")
            for cmd in sorted(set(unknown_cmds)):
                count = unknown_cmds.count(cmd)
                print(f"  0x{cmd:04x} : {count} 次")

    def print_unknown_details(self, limit: int = 10):
        """打印未知包的详细信息"""
        unknown_packets = [p for p in self.packets
                          if p.cmd and not TdxCommandRegistry.is_known(p.cmd)]

        if not unknown_packets:
            print("\n[INFO] 没有发现未知命令")
            return

        print("\n" + "=" * 70)
        print(f"未知数据包详情 (显示前 {min(limit, len(unknown_packets))} 个)")
        print("=" * 70)

        for i, pkt in enumerate(unknown_packets[:limit]):
            direction = "→ 请求" if pkt.is_request else "← 响应"
            print(f"\n[{i+1}] {direction} Cmd=0x{pkt.cmd:04x}")
            print(f"    时间: {datetime.fromtimestamp(pkt.timestamp)}")
            print(f"    来源: {pkt.src_ip}:{pkt.src_port} -> {pkt.dst_ip}:{pkt.dst_port}")
            print(f"    长度: {len(pkt.payload)} bytes")
            print(f"    Hex (前 48 bytes):")
            self._print_hex(pkt.payload[:48], indent=8)

    def print_all_packets(self, show_hex: bool = False, only_unknown: bool = False):
        """打印所有数据包"""
        print("\n" + "=" * 70)
        print("数据包详情")
        print("=" * 70)

        for i, pkt in enumerate(self.packets):
            if only_unknown and TdxCommandRegistry.is_known(pkt.cmd):
                continue

            direction = "→ 请求" if pkt.is_request else "← 响应"
            known_mark = "✓" if TdxCommandRegistry.is_known(pkt.cmd) else "?"

            print(f"\n[{i+1:3d}] [{known_mark}] {direction} {pkt.cmd_name}")
            print(f"      {pkt.src_ip}:{pkt.src_port} -> {pkt.dst_ip}:{pkt.dst_port}")

            if pkt.parsed_data:
                self._print_parsed_data(pkt.parsed_data)

            if show_hex:
                print(f"      Hex ({min(64, len(pkt.payload))} bytes):")
                self._print_hex(pkt.payload[:64], indent=8)

    def _print_parsed_data(self, data: Dict, indent: int = 6):
        """打印解析后的数据"""
        for key, value in data.items():
            if key == 'stocks' and isinstance(value, list):
                print(f"{' '*indent}{key}:")
                for stock in value[:5]:  # 最多显示5只
                    print(f"{' '*indent}  - {stock.get('market_name', '?')} {stock.get('code', '?')}")
                if len(value) > 5:
                    print(f"{' '*indent}  ... 还有 {len(value) - 5} 只")
            elif key != 'type':
                print(f"{' '*indent}{key}: {value}")

    def _print_hex(self, data: bytes, indent: int = 0, width: int = 16):
        """打印 hex dump"""
        for i in range(0, len(data), width):
            chunk = data[i:i+width]
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"{' '*indent}{i:04x}  {hex_part:<{width*3}}  {ascii_part}")

    def export_unknown(self, output_file: str):
        """导出未知包信息到 JSON"""
        unknown_packets = [p for p in self.packets
                          if p.cmd and not TdxCommandRegistry.is_known(p.cmd)]

        export_data = []
        for pkt in unknown_packets:
            export_data.append({
                'timestamp': pkt.timestamp,
                'datetime': datetime.fromtimestamp(pkt.timestamp).isoformat(),
                'src_ip': pkt.src_ip,
                'dst_ip': pkt.dst_ip,
                'src_port': pkt.src_port,
                'dst_port': pkt.dst_port,
                'is_request': pkt.is_request,
                'cmd': f"0x{pkt.cmd:04x}",
                'payload_len': len(pkt.payload),
                'payload_hex': pkt.payload.hex(),
                'header_hex': pkt.payload[:16].hex() if len(pkt.payload) >= 16 else None
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"\n[INFO] 已导出 {len(export_data)} 个未知包到 {output_file}")

    def analyze_unknown_patterns(self):
        """分析未知包的模式"""
        unknown_packets = [p for p in self.packets
                          if p.cmd and not TdxCommandRegistry.is_known(p.cmd)]

        if not unknown_packets:
            return

        print("\n" + "=" * 70)
        print("未知命令模式分析")
        print("=" * 70)

        # 按命令分组
        by_cmd = defaultdict(list)
        for pkt in unknown_packets:
            by_cmd[pkt.cmd].append(pkt)

        for cmd, packets in sorted(by_cmd.items()):
            print(f"\n命令 0x{cmd:04x} ({len(packets)} 次):")

            # 分析包大小分布
            sizes = [len(p.payload) for p in packets]
            print(f"  包大小范围: {min(sizes)} - {max(sizes)} bytes")

            # 分析请求/响应比例
            req_count = sum(1 for p in packets if p.is_request)
            resp_count = len(packets) - req_count
            print(f"  请求: {req_count}, 响应: {resp_count}")

            # 显示第一个包的示例
            first_pkt = packets[0]
            print(f"  示例包 ({'请求' if first_pkt.is_request else '响应'}):")
            print(f"    Hex (前 32 bytes):")
            self._print_hex(first_pkt.payload[:32], indent=6)


def main():
    parser = argparse.ArgumentParser(
        description='TDX Protocol PCAP Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    %(prog)s capture.pcapng                    # 完整分析
    %(prog)s capture.pcapng --summary          # 只显示摘要
    %(prog)s capture.pcapng --unknown          # 只显示未知包
    %(prog)s capture.pcapng --export unknown.json  # 导出未知包
    %(prog)s capture.pcapng --hex              # 显示 hex dump
        '''
    )

    parser.add_argument('pcap_file', help='PCAP/PCAPNG 文件路径')
    parser.add_argument('--port', type=int, default=7709, help='TDX 端口 (默认: 7709)')
    parser.add_argument('--summary', action='store_true', help='只显示摘要')
    parser.add_argument('--unknown', action='store_true', help='只显示未知包详情')
    parser.add_argument('--export', metavar='FILE', help='导出未知包到 JSON 文件')
    parser.add_argument('--hex', action='store_true', help='显示 hex dump')

    args = parser.parse_args()

    # 创建分析器
    analyzer = TdxPcapAnalyzer(args.pcap_file, args.port)
    analyzer.load_pcap()

    # 输出结果
    if args.summary:
        analyzer.print_summary()
    elif args.unknown:
        analyzer.print_summary()
        analyzer.print_unknown_details()
        analyzer.analyze_unknown_patterns()
    else:
        analyzer.print_summary()
        analyzer.print_all_packets(show_hex=args.hex)

    # 导出
    if args.export:
        analyzer.export_unknown(args.export)


if __name__ == '__main__':
    main()
