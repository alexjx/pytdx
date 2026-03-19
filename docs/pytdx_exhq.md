# 扩展行情接口 API（`pytdx.exhq.TdxExHq_API`）

本文档采用统一结构：

- 描述
- 输入（表格）
- 输出（表格）
- 注意事项
- 样例（可选）

## 快速开始

```python
from pytdx.exhq import TdxExHq_API

api = TdxExHq_API()
with api.connect('61.152.107.141', 7727):
    rows = api.get_markets()
```

## 通用约定

### 日期格式

| 参数 | 格式 | 示例 |
| --- | --- | --- |
| `date` | `YYYYMMDD` | `20260319` |

### `to_df` 转换规则

| 输入类型 | 输出 |
| --- | --- |
| `list` | `DataFrame(v)` |
| `dict/OrderedDict` | `DataFrame([v])` |
| 其它（如 `int/str`） | `DataFrame([{"value": v}])` |

### K 线周期（`category`）

| 值 | 常量 | 含义 |
| --- | --- | --- |
| `0` | `KLINE_TYPE_5MIN` | 5 分钟 |
| `1` | `KLINE_TYPE_15MIN` | 15 分钟 |
| `2` | `KLINE_TYPE_30MIN` | 30 分钟 |
| `3` | `KLINE_TYPE_1HOUR` | 1 小时 |
| `4` | `KLINE_TYPE_DAILY` | 日线 |
| `5` | `KLINE_TYPE_WEEKLY` | 周线 |
| `6` | `KLINE_TYPE_MONTHLY` | 月线 |
| `7` | `KLINE_TYPE_EXHQ_1MIN` | 扩展 1 分钟 |
| `8` | `KLINE_TYPE_1MIN` | 1 分钟 |
| `9` | `KLINE_TYPE_RI_K` | 日线（兼容） |
| `10` | `KLINE_TYPE_3MONTH` | 季线 |
| `11` | `KLINE_TYPE_YEARLY` | 年线 |

## API 总览

| API | 描述 | 输出类型 |
| --- | --- | --- |
| `get_markets` | 获取主站支持的扩展市场 | `list[OrderedDict]` |
| `get_instrument_info` | 分页获取代码列表 | `list[OrderedDict]` |
| `get_instrument_count` | 获取扩展市场总代码数量 | `int` |
| `get_instrument_quote` | 获取单标的五档快照 | `list[OrderedDict]` |
| `get_instrument_quote_list` | 按市场/品类批量获取行情 | `list[OrderedDict]` |
| `get_minute_time_data` | 获取当日分时 | `list[OrderedDict]` |
| `get_history_minute_time_data` | 获取历史分时 | `list[OrderedDict]` |
| `get_instrument_bars` | 获取扩展市场 K 线 | `list[OrderedDict]` |
| `get_transaction_data` | 获取当日分笔 | `list[OrderedDict]` |
| `get_history_transaction_data` | 获取历史分笔 | `list[OrderedDict]` |
| `get_history_instrument_bars_range` | 按区间获取历史 K 线 | `list[OrderedDict]` |

## 字段命名对照（交易语境）

以下是文档中常见拼音/英文混合字段的推荐中文理解，便于和交易终端术语对齐。

### 通用盘口与量价

| 字段 | 交易语义（建议中文） |
| --- | --- |
| `pre_close` | 昨收 |
| `open` | 今开 |
| `high` | 最高 |
| `low` | 最低 |
| `price` / `XianJia` / `MaiChu` | 最新价（现价） |
| `avg_price` | 均价 |
| `volume` / `trade` | 成交量 |
| `amount` / `ZongJinE` | 成交额 |
| `position` / `chicang` / `ChiCangLiang` | 持仓量 |
| `open_interest` | 持仓量（分时口径） |
| `zongliang` / `ZongLiang` | 总量 |
| `xianliang` / `XianLiang` | 现量 |
| `neipan` / `NeiPan` / `Nei` | 内盘 |
| `waipan` / `WaiPan` / `Wai` | 外盘 |
| `kaicang` / `KaiCang` | 开仓量/开仓相关字段 |
| `zengcang` | 增仓 |
| `BiShu` | 成交笔数（按品种口径） |
| `HuoYueDu` | 活跃度 |
| `ZuoShou` / `ZuoJie` | 昨收（结） |
| `JinKai` | 今开 |
| `ZuiGao` | 最高 |
| `ZuiDi` | 最低 |

### 买卖盘（档位）

| 字段 | 交易语义（建议中文） |
| --- | --- |
| `bid1..bid5` | 买一到买五价 |
| `bid_vol1..bid_vol5` | 买一到买五量 |
| `ask1..ask5` | 卖一到卖五价 |
| `ask_vol1..ask_vol5` | 卖一到卖五量 |
| `MaiRuJia` | 买入价/买盘价（上下文相关） |
| `MaiRuJia1..5` | 买一到买五价 |
| `MaiRuLiang` / `MaiRuLiang1..5` | 买量/买一到买五量 |
| `MaiChuJia` / `MaiChuJia1..5` | 卖价/卖一到卖五价 |
| `MaiChuLiang` / `MaiChuLiang1..5` | 卖量/卖一到卖五量 |

### 成交方向与性质

| 字段 | 交易语义（建议中文） |
| --- | --- |
| `nature` | 原始成交性质编码 |
| `nature_mark` | 成交性质主标记 |
| `nature_value` | 成交性质附加值 |
| `nature_name` | 成交性质中文（如多开、空平、B、S） |
| `direction` | 方向归一值（买/卖/中性） |
| `natrue_name` | `nature_name` 的兼容拼写字段 |

---

## 1) `get_markets`

### 描述

获取当前扩展行情主站支持的市场列表。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| 无 | - | - | 无参数 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `market` | `int` | 市场 ID |
| `category` | `int` | 品类 ID |
| `name` | `str` | 市场名称 |
| `short_name` | `str` | 市场简称 |

### 注意事项

- 后续 `market` 参数建议都从本接口结果中获取。

### 样例

```python
api.get_markets()
```

---

## 2) `get_instrument_info`

### 描述

分页获取代码列表。

### 输入

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `start` | `int` | 是 | - | 起始偏移 |
| `count` | `int` | 否 | `100` | 请求条数 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `category` | `int` | 品类 ID |
| `market` | `int` | 市场 ID |
| `code` | `str` | 合约/证券代码 |
| `name` | `str` | 名称 |
| `desc` | `str` | 扩展描述 |

### 注意事项

- 建议先缓存本接口结果，再按需增量更新。

### 样例

```python
api.get_instrument_info(0, 100)
```

---

## 3) `get_instrument_count`

### 描述

获取扩展市场总代码数量。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| 无 | - | - | 无参数 |

### 输出

返回类型：`int`

| 值 | 类型 | 说明 |
| --- | --- | --- |
| 总数量 | `int` | 扩展市场可查询代码总数 |

### 注意事项

- 可结合 `get_instrument_info` 做分页上界控制。

### 样例

```python
api.get_instrument_count()
```

---

## 4) `get_instrument_quote`

### 描述

获取单标的五档快照。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场 ID |
| `code` | `str` | 是 | 合约/证券代码 |

### 输出

返回类型：`list[OrderedDict]`（通常长度为 1）

| 字段组 | 代表字段 | 说明 |
| --- | --- | --- |
| 标识字段 | `market`, `code` | 市场与代码 |
| 基础行情 | `pre_close`, `open`, `high`, `low`, `price` | 昨收/开高低现 |
| 量仓字段 | `kaicang`, `zongliang`, `xianliang`, `neipan`, `waipan`, `chicang` | 开仓量/成交量/持仓等 |
| 五档买盘 | `bid1..bid5`, `bid_vol1..bid_vol5` | 买价与买量 |
| 五档卖盘 | `ask1..ask5`, `ask_vol1..ask_vol5` | 卖价与卖量 |

### 注意事项

- 返回是 `list`，不是单个 `dict`。
- 拼音字段中文语义见上文“字段命名对照（交易语境）”。

### 样例

```python
api.get_instrument_quote(47, 'IFL0')
```

---

## 5) `get_instrument_quote_list`

### 描述

按市场与品类批量获取行情列表。

### 输入

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `market` | `int` | 是 | - | 市场 ID |
| `category` | `int` | 是 | - | 品类 ID |
| `start` | `int` | 否 | `0` | 起始偏移 |
| `count` | `int` | 否 | `80` | 请求条数 |

### 输出

返回类型：`list[OrderedDict]`

| 场景 | 字段 |
| --- | --- |
| `category=2`（港股类） | `market, code, HuoYueDu, ZuoShou, JinKai, ZuiGao, ZuiDi, XianJia, MaiRuJia, ZongLiang, XianLiang, ZongJinE, Nei, Wai, MaiRuJia1..5, MaiRuLiang1..5, MaiChuJia1..5, MaiChuLiang1..5` |
| `category=3`（期货类） | `market, code, BiShu, ZuoJie, JinKai, ZuiGao, ZuiDi, MaiChu, KaiCang, ZongLiang, XianLiang, ZongJinE, NeiPan, WaiPan, ChiCangLiang, MaiRuJia, MaiRuLiang, MaiChuJia, MaiChuLiang` |

### 注意事项

- 当前实现只支持 `category in [2, 3]`。
- 字段中文语义见上文“字段命名对照（交易语境）”。

### 样例

```python
api.get_instrument_quote_list(29, 3, 0, 10)
```

---

## 6) `get_minute_time_data`

### 描述

获取当日分时。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场 ID |
| `code` | `str` | 是 | 合约/证券代码 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `hour`, `minute` | `int` | 时间 |
| `price` | `float` | 当前价 |
| `avg_price` | `float` | 均价 |
| `volume` | `int` | 成交量 |
| `open_interest` | `int` | 持仓量/扩展量字段 |

### 注意事项

- 字段语义会因品种差异略有不同，尤其是 `open_interest`。
- 拼音字段中文语义见上文“字段命名对照（交易语境）”。

### 样例

```python
api.get_minute_time_data(47, 'IFL0')
```

---

## 7) `get_history_minute_time_data`

### 描述

获取历史某日分时。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场 ID |
| `code` | `str` | 是 | 合约/证券代码 |
| `date` | `int` | 是 | `YYYYMMDD` |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `hour`, `minute` | `int` | 时间 |
| `price` | `float` | 当前价 |
| `avg_price` | `float` | 均价 |
| `volume` | `int` | 成交量 |
| `open_interest` | `int` | 持仓量/扩展量字段 |

### 注意事项

- 无数据时返回空列表。

### 样例

```python
api.get_history_minute_time_data(31, '00020', 20170811)
```

---

## 8) `get_instrument_bars`

### 描述

获取扩展市场 K 线。

### 输入

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `category` | `int` | 是 | - | K 线周期 |
| `market` | `int` | 是 | - | 市场 ID |
| `code` | `str` | 是 | - | 合约/证券代码 |
| `start` | `int` | 否 | `0` | 起始偏移 |
| `count` | `int` | 否 | `700` | 请求条数 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `open`, `high`, `low`, `close` | `float` | OHLC |
| `position` | `int` | 持仓 |
| `trade` | `int` | 成交量 |
| `price` | `float` | 价格字段（按品种解释） |
| `amount` | `float` | 成交额 |
| `year`, `month`, `day`, `hour`, `minute`, `datetime` | `int/str` | 时间 |

### 注意事项

- `count` 过大时建议分页拉取。

### 样例

```python
from pytdx.params import TDXParams

api.get_instrument_bars(TDXParams.KLINE_TYPE_DAILY, 31, '00020', 0, 100)
```

---

## 9) `get_transaction_data`

### 描述

获取当日分笔成交。

### 输入

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `market` | `int` | 是 | - | 市场 ID |
| `code` | `str` | 是 | - | 合约/证券代码 |
| `start` | `int` | 否 | `0` | 起始偏移 |
| `count` | `int` | 否 | `1800` | 请求条数 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `date` | `datetime` | 成交时间 |
| `hour`, `minute`, `second` | `int` | 拆分时间 |
| `price` | `int` | 成交价（原始单位） |
| `volume` | `int` | 成交量 |
| `zengcang` | `int` | 增仓 |
| `nature` | `int` | 原始方向/性质标识 |
| `nature_mark`, `nature_value` | `int` | `nature` 拆分值 |
| `nature_name` | `str` | 可读方向（如 `多开/空平/B/S`） |
| `direction` | `int` | 方向归一值（`1/-1/0`） |

### 注意事项

- 港股市场（如 `31/48`）会按 `B/S` 规则映射。
- `nature*`、`direction` 字段建议结合“字段命名对照（交易语境）”阅读。

### 样例

```python
api.get_transaction_data(31, '00020', 0, 1800)
```

---

## 10) `get_history_transaction_data`

### 描述

获取历史分笔成交。

### 输入

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `market` | `int` | 是 | - | 市场 ID |
| `code` | `str` | 是 | - | 合约/证券代码 |
| `date` | `int` | 是 | - | `YYYYMMDD` |
| `start` | `int` | 否 | `0` | 起始偏移 |
| `count` | `int` | 否 | `1800` | 请求条数 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `date` | `datetime` | 成交时间 |
| `hour`, `minute` | `int` | 拆分时间 |
| `price` | `int` | 成交价（原始单位） |
| `volume` | `int` | 成交量 |
| `zengcang` | `int` | 增仓 |
| `nature` | `int` | 原始方向/性质标识 |
| `direction` | `int` | 方向归一值（`1/-1/0`） |
| `nature_name` | `str` | 可读方向 |
| `natrue_name` | `str` | 兼容字段（历史拼写） |

### 注意事项

- `natrue_name` 为兼容保留字段，建议优先使用 `nature_name`。
- 无数据时返回空列表。
- `nature*`、`direction` 字段建议结合“字段命名对照（交易语境）”阅读。

### 样例

```python
api.get_history_transaction_data(31, '00020', 20170811, 0, 1800)
```

---

## 11) `get_history_instrument_bars_range`

### 描述

按日期区间获取历史 K 线。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场 ID |
| `code` | `str` | 是 | 合约/证券代码 |
| `start` | `int` | 是 | 起始日期 `YYYYMMDD` |
| `end` | `int` | 是 | 结束日期 `YYYYMMDD` |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `datetime` | `str` | 时间字符串 |
| `year`, `month`, `day`, `hour`, `minute` | `int` | 拆分时间 |
| `open`, `high`, `low`, `close` | `float` | OHLC |
| `position` | `int` | 持仓 |
| `trade` | `int` | 成交量 |
| `settlementprice` | `float` | 结算价 |

### 注意事项

- 具体可用区间受服务端历史数据覆盖范围影响。

### 样例

```python
api.get_history_instrument_bars_range(74, 'BABA', 20170613, 20170620)
```

---

## 运行选项（非业务 API）

| 选项 | 构造参数 | 说明 |
| --- | --- | --- |
| 多线程 | `multithread=True` | 并发请求时可用 |
| 心跳 | `heartbeat=True` | 空闲保活，自动启用多线程 |
| 异常模式 | `raise_exception=True` | 失败抛 `TdxConnectionError` / `TdxFunctionCallError` |
| 自动重试 | `auto_retry=True` | 断连时按策略自动重连 |

## 流量统计

```python
api.get_traffic_stats()
```
