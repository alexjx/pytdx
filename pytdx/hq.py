# coding=utf-8

#
# Just for practising
#


import datetime
import json
import os
import random
import socket
import struct
import sys
import threading

import pandas as pd
from pytdx.base_socket_client import BaseSocketClient, update_last_ack_time
from pytdx.heartbeat import HqHeartBeatThread
from pytdx.log import DEBUG, log
from pytdx.params import TDXParams
from pytdx.parser.get_block_info import (GetBlockInfo, GetBlockInfoMeta,
                                         get_and_parse_block_info)
from pytdx.parser.get_company_info_category import GetCompanyInfoCategory
from pytdx.parser.get_company_info_content import GetCompanyInfoContent
from pytdx.parser.get_finance_info import GetFinanceInfo
from pytdx.parser.get_history_minute_time_data import GetHistoryMinuteTimeData
from pytdx.parser.get_history_transaction_data import GetHistoryTransactionData
from pytdx.parser.get_index_bars import GetIndexBarsCmd
from pytdx.parser.get_minute_time_data import GetMinuteTimeData
from pytdx.parser.get_security_bars import GetSecurityBarsCmd
from pytdx.parser.get_security_count import GetSecurityCountCmd
from pytdx.parser.get_security_list import GetSecurityList
from pytdx.parser.get_security_quotes import GetSecurityQuotesCmd
from pytdx.parser.get_transaction_data import GetTransactionData
from pytdx.parser.get_xdxr_info import GetXdXrInfo
from pytdx.parser.get_report_file import GetReportFile
from pytdx.parser.setup_commands import SetupCmd1, SetupCmd2, SetupCmd3
from pytdx.util import get_real_trade_date, trade_date_sse
try:
    # Python 3
    from collections.abc import Iterable
except ImportError:
    # Python 2.7
    from collections import Iterable

if __name__ == '__main__':
    sys.path.append(os.path.dirname(
        os.path.dirname(os.path.realpath(__file__))))


class TdxHq_API(BaseSocketClient):

    def setup(self):
        SetupCmd1(self.client).call_api()
        SetupCmd2(self.client).call_api()
        SetupCmd3(self.client).call_api()

    # API List

    # Notice：，如果一个股票当天停牌，那天的K线还是能取到，成交量为0
    @update_last_ack_time
    def get_security_bars(self, category, market, code, start, count):
        cmd = GetSecurityBarsCmd(self.client, lock=self.lock)
        cmd.setParams(category, market, code, start, count)
        return cmd.call_api()

    @update_last_ack_time
    def get_index_bars(self, category, market, code, start, count):
        cmd = GetIndexBarsCmd(self.client, lock=self.lock)
        cmd.setParams(category, market, code, start, count)
        return cmd.call_api()

    @update_last_ack_time
    def get_security_quotes(self, all_stock, code=None):
        """
        支持三种形式的参数
        get_security_quotes(market, code )
        get_security_quotes((market, code))
        get_security_quotes([(market1, code1), (market2, code2)] )
        :param all_stock （market, code) 的数组
        :param code{optional} code to query
        :return:
        """

        if code is not None:
            all_stock = [(all_stock, code)]
        elif (isinstance(all_stock, list) or isinstance(all_stock, tuple))\
                and len(all_stock) == 2 and type(all_stock[0]) is int:
            all_stock = [all_stock]

        cmd = GetSecurityQuotesCmd(self.client, lock=self.lock)
        cmd.setParams(all_stock)
        return cmd.call_api()

    @update_last_ack_time
    def get_market_quotes_snapshot(self, all_stock=None, code_list=None, market_hint=None):
        """
        socket版行情快照封装（底层仍为 0x6320）

        参数两种方式：
        1. all_stock=[(market, code), ...]
        2. code_list=['920088','513350', ...]  # 自动推断市场
        """
        if all_stock is None:
            if not code_list:
                return []
            all_stock = [(_select_market_code(code), str(code))
                         for code in code_list]

        rows = self.get_security_quotes(all_stock) or []
        if market_hint is not None:
            rows = [r for r in rows if r.get("market") == market_hint]
        if code_list:
            keep = set([str(x) for x in code_list])
            rows = [r for r in rows if r.get("code") in keep]
        return rows

    def _build_etf_panel_init_pkg(self, panel_path):
        # 0x7c2c: init path, observed fixed body length 40
        path40 = panel_path.encode("ascii")[:40]
        path40 += b"\x00" * (40 - len(path40))
        return bytearray.fromhex("0c012c7c00012a002a00c502") + path40

    def _build_etf_panel_warmup_pkg(self, market, code):
        # 0xc920: warmup quote request, template observed from capture
        pkg = bytearray.fromhex(
            "0c0320c908010f000f00470501000031353939313900000000")
        pkg[17] = int(market) & 0xFF
        code6 = str(code).encode("ascii", "ignore")[:6]
        pkg[19:25] = code6 + b"\x00" * (6 - len(code6))
        return pkg

    def _build_etf_panel_pull_pkg(self, seq_index, offset, chunk_size, panel_path):
        # 0x7d2c: chunk pull, observed fixed body length 300
        path300 = panel_path.encode("ascii")[:300]
        path300 += b"\x00" * (300 - len(path300))
        head = struct.pack(
            "<HHHHHHII",
            0x020C + seq_index * 0x0100,
            0x7D2C,
            0x0100,
            0x0136,
            0x0136,
            0x06B9,
            offset,
            chunk_size,
        )
        return head + path300

    @update_last_ack_time
    def get_etf_panel_table(self,
                            panel_path="bi_diy/list/gxjty_etfjj101.jsn",
                            warmup_stock=(TDXParams.MARKET_SZ, "159919"),
                            chunk_size=30000,
                            max_chunks=12,
                            focus_codes=None):
        """
        socket版ETF面板表格拉取（实验）
        时序：0x7c2c(init) -> 0xc920(warmup) -> 0x7d2c(offset分块)
        """
        blob = bytearray()
        offsets = []

        self.send_raw_pkg(self._build_etf_panel_init_pkg(panel_path))
        if warmup_stock:
            market, code = warmup_stock
            self.send_raw_pkg(self._build_etf_panel_warmup_pkg(market, code))

        for i in range(max_chunks):
            offset = i * chunk_size
            rsp = self.send_raw_pkg(self._build_etf_panel_pull_pkg(
                i, offset, chunk_size, panel_path))
            if not rsp or len(rsp) < 4:
                break
            got = struct.unpack("<I", rsp[:4])[0]
            if got <= 0:
                break
            blob.extend(rsp[4:4 + got])
            offsets.append(offset)
            if got < chunk_size:
                break

        start = blob.find(b"{")
        end = blob.rfind(b"}")
        if start < 0 or end <= start:
            return {
                "columns": [],
                "rows": [],
                "offsets": offsets,
                "incomplete": True,
                "focus_rows": {},
                "errors": ["cannot find JSON body in chunk stream"],
            }

        try:
            obj = json.loads(blob[start:end + 1].decode("utf-8"))
        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "offsets": offsets,
                "incomplete": True,
                "focus_rows": {},
                "errors": ["json decode failed: {}".format(e)],
            }

        rows = obj.get("data", [])
        focus_rows = {}
        if focus_codes:
            for code in focus_codes:
                code = str(code)
                hit = next((r for r in rows if len(r) > 0 and str(r[0]) == code), None)
                if hit:
                    focus_rows[code] = hit

        return {
            "columns": obj.get("colheader", []),
            "rows": rows,
            "offsets": offsets,
            "incomplete": len(offsets) >= max_chunks and len(rows) > 0,
            "focus_rows": focus_rows,
            "errors": [],
        }

    @update_last_ack_time
    def get_security_count(self, market):
        cmd = GetSecurityCountCmd(self.client, lock=self.lock)
        cmd.setParams(market)
        return cmd.call_api()

    @update_last_ack_time
    def get_security_list(self, market, start):
        cmd = GetSecurityList(self.client, lock=self.lock)
        cmd.setParams(market, start)
        return cmd.call_api()

    @update_last_ack_time
    def get_minute_time_data(self, market, code):
        cmd = GetMinuteTimeData(self.client, lock=self.lock)
        cmd.setParams(market, code)
        return cmd.call_api()

    @update_last_ack_time
    def get_history_minute_time_data(self, market, code, date):
        cmd = GetHistoryMinuteTimeData(self.client, lock=self.lock)
        cmd.setParams(market, code, date)
        return cmd.call_api()

    @update_last_ack_time
    def get_transaction_data(self, market, code, start, count):
        cmd = GetTransactionData(self.client, lock=self.lock)
        cmd.setParams(market, code, start, count)
        return cmd.call_api()

    @update_last_ack_time
    def get_history_transaction_data(self, market, code, start, count, date):
        cmd = GetHistoryTransactionData(self.client, lock=self.lock)
        cmd.setParams(market, code, start, count, date)
        return cmd.call_api()

    @update_last_ack_time
    def get_company_info_category(self, market, code):
        cmd = GetCompanyInfoCategory(self.client, lock=self.lock)
        cmd.setParams(market, code)
        return cmd.call_api()

    @update_last_ack_time
    def get_company_info_content(self, market, code, filename, start, length):
        result = ""
        cmd = GetCompanyInfoContent(self.client, lock=self.lock)
        while cmd.retry_send:
            cmd.setParams(market, code, filename, start, length)
            result += cmd.call_api()
            start += 30720
            length -= 30720
        return result

    @update_last_ack_time
    def get_xdxr_info(self, market, code):
        cmd = GetXdXrInfo(self.client, lock=self.lock)
        cmd.setParams(market, code)
        return cmd.call_api()

    @update_last_ack_time
    def get_finance_info(self, market, code):
        cmd = GetFinanceInfo(self.client, lock=self.lock)
        cmd.setParams(market, code)
        return cmd.call_api()

    @update_last_ack_time
    def get_block_info_meta(self, blockfile):
        cmd = GetBlockInfoMeta(self.client, lock=self.lock)
        cmd.setParams(blockfile)
        return cmd.call_api()

    @update_last_ack_time
    def get_block_info(self, blockfile, start, size):
        cmd = GetBlockInfo(self.client, lock=self.lock)
        cmd.setParams(blockfile, start, size)
        return cmd.call_api()

    def get_and_parse_block_info(self, blockfile):
        return get_and_parse_block_info(self, blockfile)

    @update_last_ack_time
    def get_report_file(self, filename, offset):
        cmd = GetReportFile(self.client, lock=self.lock)
        cmd.setParams(filename, offset)
        return cmd.call_api()

    def get_report_file_by_size(self, filename, filesize=0, reporthook=None):
        """
        Download file from proxy server

        :param filename the filename to download
        :param filesize the filesize to download , if you do not known the actually filesize, leave this value 0
        """
        filecontent = bytearray(filesize)
        current_downloaded_size = 0
        get_zero_length_package_times = 0
        while current_downloaded_size < filesize or filesize == 0:
            response = self.get_report_file(filename, current_downloaded_size)
            if response["chunksize"] > 0:
                current_downloaded_size = current_downloaded_size + \
                    response["chunksize"]
                filecontent.extend(response["chunkdata"])
                if reporthook is not None:
                    reporthook(current_downloaded_size,filesize)
            else:
                get_zero_length_package_times = get_zero_length_package_times + 1
                if filesize == 0:
                    break
                elif get_zero_length_package_times > 2:
                    break

        return filecontent

    def do_heartbeat(self):
        self.get_security_count(random.randint(0, 1))

    def get_k_data(self, code, start_date, end_date):
        # 具体详情参见 https://github.com/rainx/pytdx/issues/5
        # 具体详情参见 https://github.com/rainx/pytdx/issues/21
        # https://github.com/rainx/pytdx/issues/33
        # 0 - 深圳，1 - 上海，2 - 北京（北交所）

        data = pd.concat([self.to_df(self.get_security_bars(9, _select_market_code(
            code), code, (9 - i) * 800, 800)) for i in range(10)], axis=0)

        data = data.assign(date=data['datetime'].apply(lambda x: str(x)[0:10])).assign(code=str(code))\
            .set_index('date', drop=False, inplace=False)\
            .drop(['year', 'month', 'day', 'hour', 'minute', 'datetime'], axis=1)[start_date:end_date]
        return data.assign(date=data['date'].apply(lambda x: str(x)[0:10]))


def _select_market_code(code):
    code = str(code)
    # 北交所代码：920xxx（存量兼容里 4/8 开头也按北京处理）
    if code.startswith("92") or code[0] in ["4", "8"]:
        return TDXParams.MARKET_BJ
    if code[0] in ['5', '6', '9'] or code[:3] in ["009", "126", "110", "201", "202", "203", "204"]:
        return TDXParams.MARKET_SH
    return TDXParams.MARKET_SZ


if __name__ == '__main__':
    import pprint

    api = TdxHq_API()
    if api.connect('101.227.73.20', 7709):
        log.info("获取股票行情")
        stocks = api.get_security_quotes([(0, "000001"), (1, "600300")])
        pprint.pprint(stocks)
        log.info("获取k线")
        data = api.get_security_bars(9, 0, '000001', 4, 3)
        pprint.pprint(data)
        log.info("获取 深市 股票数量")
        pprint.pprint(api.get_security_count(0))
        log.info("获取股票列表")
        stocks = api.get_security_list(1, 255)
        pprint.pprint(stocks)
        log.info("获取指数k线")
        data = api.get_index_bars(9, 1, '000001', 1, 2)
        pprint.pprint(data)
        log.info("查询分时行情")
        data = api.get_minute_time_data(TDXParams.MARKET_SH, '600300')
        pprint.pprint(data)
        log.info("查询历史分时行情")
        data = api.get_history_minute_time_data(
            TDXParams.MARKET_SH, '600300', 20161209)
        pprint.pprint(data)
        log.info("查询分时成交")
        data = api.get_transaction_data(TDXParams.MARKET_SZ, '000001', 0, 30)
        pprint.pprint(data)
        log.info("查询历史分时成交")
        data = api.get_history_transaction_data(
            TDXParams.MARKET_SZ, '000001', 0, 10, 20170209)
        pprint.pprint(data)
        log.info("查询公司信息目录")
        data = api.get_company_info_category(TDXParams.MARKET_SZ, '000001')
        pprint.pprint(data)
        log.info("读取公司信息-最新提示")
        data = api.get_company_info_content(0, '000001', '000001.txt', 0, 10)
        pprint.pprint(data)
        log.info("读取除权除息信息")
        data = api.get_xdxr_info(1, '600300')
        pprint.pprint(data)
        log.info("读取财务信息")
        data = api.get_finance_info(0, '000001')
        pprint.pprint(data)
        log.info("日线级别k线获取函数")
        data = api.get_k_data('000001', '2017-07-01', '2017-07-10')
        pprint.pprint(data)

        api.disconnect()
