#!/usr/bin/env python3
"""
TDX PCAP Analyzer - 使用示例
展示如何使用分析器模块
"""

import sys
sys.path.insert(0, '/home/xinj/pytdx')

from analyze import TdxPcapAnalyzer, TdxCommandRegistry


def example_basic_analysis():
    """示例1: 基本分析"""
    print("=" * 70)
    print("示例1: 基本分析")
    print("=" * 70)

    # 创建分析器 (假设有 capture.pcapng 文件)
    analyzer = TdxPcapAnalyzer("capture.pcapng", port=7709)

    try:
        analyzer.load_pcap()
    except Exception as e:
        print(f"[注意] 无法加载 pcap 文件: {e}")
        print("请确保有 capture.pcapng 文件在当前目录")
        return

    # 打印摘要
    analyzer.print_summary()


def example_find_unknown():
    """示例2: 查找并分析未知包"""
    print("\n" + "=" * 70)
    print("示例2: 查找未知包")
    print("=" * 70)

    analyzer = TdxPcapAnalyzer("capture.pcapng", port=7709)

    try:
        analyzer.load_pcap()
    except:
        print("[注意] 请确保有 capture.pcapng 文件")
        return

    # 找出未知包
    unknown_packets = [
        p for p in analyzer.packets
        if p.cmd and not TdxCommandRegistry.is_known(p.cmd)
    ]

    print(f"\n发现 {len(unknown_packets)} 个未知包")

    for i, pkt in enumerate(unknown_packets[:5]):
        direction = "请求" if pkt.is_request else "响应"
        print(f"\n[{i+1}] 未知命令 0x{pkt.cmd:04x} ({direction})")
        print(f"    时间戳: {pkt.timestamp}")
        print(f"    来源: {pkt.src_ip}:{pkt.src_port}")
        print(f"    目标: {pkt.dst_ip}:{pkt.dst_port}")
        print(f"    Payload (hex): {pkt.payload[:32].hex()}")


def example_analyze_quotes():
    """示例3: 分析行情请求"""
    print("\n" + "=" * 70)
    print("示例3: 分析行情请求")
    print("=" * 70)

    analyzer = TdxPcapAnalyzer("capture.pcapng", port=7709)

    try:
        analyzer.load_pcap()
    except:
        print("[注意] 请确保有 capture.pcapng 文件")
        return

    # 筛选行情请求 (0x0463)
    quote_requests = [
        p for p in analyzer.packets
        if p.cmd == 0x0463 and p.is_request
    ]

    print(f"\n找到 {len(quote_requests)} 个行情请求")

    for pkt in quote_requests[:3]:
        if 'stocks' in pkt.parsed_data:
            stocks = pkt.parsed_data['stocks']
            print(f"\n请求时间: {pkt.timestamp}")
            print(f"请求股票数: {len(stocks)}")
            for s in stocks[:5]:
                print(f"  - {s['market_name']} {s['code']}")


def example_export_for_analysis():
    """示例4: 导出数据用于进一步分析"""
    print("\n" + "=" * 70)
    print("示例4: 导出数据")
    print("=" * 70)

    analyzer = TdxPcapAnalyzer("capture.pcapng", port=7709)

    try:
        analyzer.load_pcap()
    except:
        print("[注意] 请确保有 capture.pcapng 文件")
        return

    # 导出未知包
    analyzer.export_unknown("unknown_export.json")

    print("\n导出完成!")
    print("可以查看 unknown_export.json 进行详细分析")


if __name__ == '__main__':
    print("TDX PCAP Analyzer 使用示例")
    print("=" * 70)
    print("\n这些示例展示了如何使用分析器模块")
    print("请确保有 capture.pcapng 文件在当前目录\n")

    # 运行示例 (如果没有 pcap 文件会显示提示)
    example_basic_analysis()
    example_find_unknown()
    example_analyze_quotes()
    example_export_for_analysis()

    print("\n" + "=" * 70)
    print("提示: 使用命令行工具更灵活:")
    print("  python tdx_pcap_analyzer.py capture.pcapng --summary")
    print("  python tdx_pcap_analyzer.py capture.pcapng --unknown")
    print("=" * 70)
