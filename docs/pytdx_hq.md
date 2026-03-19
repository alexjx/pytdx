# 行情接口 API（`pytdx.hq.TdxHq_API`）

本文档只关注 API 使用本身，采用统一结构：

- 描述
- 输入（表格）
- 输出（表格）
- 注意事项
- 样例（可选）

## 快速开始

```python
from pytdx.hq import TdxHq_API

api = TdxHq_API()
with api.connect('119.147.212.81', 7709):
    rows = api.get_security_quotes([(0, '000001')])
```

## 通用约定

### 市场代码

| 值 | 含义 |
| --- | --- |
| `0` | 深圳 |
| `1` | 上海 |
| `2` | 北京（北交所） |

### K 线周期（`category`）

| 值 | 含义 |
| --- | --- |
| `0` | 5 分钟 |
| `1` | 15 分钟 |
| `2` | 30 分钟 |
| `3` | 1 小时 |
| `4` | 日线 |
| `5` | 周线 |
| `6` | 月线 |
| `7` | 1 分钟 |
| `8` | 1 分钟（兼容） |
| `9` | 日线（兼容） |
| `10` | 季线 |
| `11` | 年线 |

### `to_df` 转换规则

| 输入类型 | 输出 |
| --- | --- |
| `list` | `DataFrame(v)` |
| `dict/OrderedDict` | `DataFrame([v])` |
| 其它（如 `int/str`） | `DataFrame([{"value": v}])` |

## API 总览

| API | 描述 | 输出类型 |
| --- | --- | --- |
| `get_security_quotes` | 获取多标的五档快照 | `list[OrderedDict]` |
| `get_security_bars` | 获取个股 K 线 | `list[OrderedDict]` |
| `get_security_count` | 获取市场证券总数 | `int` |
| `get_security_list` | 获取证券列表 | `list[OrderedDict]` |
| `get_index_bars` | 获取指数 K 线 | `list[OrderedDict]` |
| `get_minute_time_data` | 获取当日分时 | `list[OrderedDict]` |
| `get_history_minute_time_data` | 获取历史分时 | `list[OrderedDict]` |
| `get_transaction_data` | 获取当日分笔 | `list[OrderedDict]` |
| `get_history_transaction_data` | 获取历史分笔 | `list[OrderedDict]` |
| `get_company_info_category` | 获取公司资料目录 | `list[OrderedDict]` |
| `get_company_info_content` | 获取公司资料正文 | `str` |
| `get_xdxr_info` | 获取除权除息/股本变动 | `list[OrderedDict]` |
| `get_finance_info` | 获取财务信息 | `OrderedDict` |
| `get_k_data` | 日线便捷接口 | `pandas.DataFrame` |
| `get_and_parse_block_info` | 获取并解析板块信息 | `list[dict]` |
| `get_market_quotes_snapshot` | 快照封装接口（`0x6320`） | `list[OrderedDict]` |
| `get_etf_panel_table` | ETF 面板实验接口 | `dict` |

## 字段命名对照（交易语境）

以下是 `hq` 文档中常见拼音字段的推荐中文理解，尽量贴近交易终端术语。

### 盘口与成交

| 字段 | 交易语义（建议中文） |
| --- | --- |
| `vol` | 成交量 |
| `cur_vol` | 现量 |
| `amount` | 成交额 |
| `s_vol` | 内盘量（卖出主动） |
| `b_vol` | 外盘量（买入主动） |
| `buyorsell` | 买卖方向标识（协议原始值） |
| `bid1..bid5` | 买一到买五价 |
| `bid_vol1..bid_vol5` | 买一到买五量 |
| `ask1..ask5` | 卖一到卖五价 |
| `ask_vol1..ask_vol5` | 卖一到卖五量 |

### 除权除息（`get_xdxr_info`）

| 字段 | 交易语义（建议中文） |
| --- | --- |
| `fenhong` | 每股分红 |
| `peigujia` | 配股价 |
| `songzhuangu` | 送转股比例 |
| `peigu` | 配股比例 |
| `suogu` | 缩股比例 |
| `panqianliutong` | 变动前流通股本 |
| `panhouliutong` | 变动后流通股本 |
| `qianzongguben` | 变动前总股本 |
| `houzongguben` | 变动后总股本 |
| `fenshu` | 权证份数/派送份数（按类别） |
| `xingquanjia` | 行权价 |

### 财务字段（`get_finance_info`）

| 字段 | 交易语义（建议中文） |
| --- | --- |
| `liutongguben` | 流通股本 |
| `zongguben` | 总股本 |
| `guojiagu` | 国家股 |
| `faqirenfarengu` | 发起人法人股 |
| `farengu` | 法人股 |
| `bgu` | B 股股本 |
| `hgu` | H 股股本 |
| `zhigonggu` | 职工股 |
| `zongzichan` | 总资产 |
| `liudongzichan` | 流动资产 |
| `gudingzichan` | 固定资产 |
| `wuxingzichan` | 无形资产 |
| `gudongrenshu` | 股东人数 |
| `liudongfuzhai` | 流动负债 |
| `changqifuzhai` | 长期负债 |
| `zibengongjijin` | 资本公积金 |
| `jingzichan` | 净资产 |
| `zhuyingshouru` | 主营收入 |
| `zhuyinglirun` | 主营利润 |
| `yingshouzhangkuan` | 应收账款 |
| `yingyelirun` | 营业利润 |
| `touzishouyu` | 投资收益 |
| `jingyingxianjinliu` | 经营现金流 |
| `zongxianjinliu` | 总现金流 |
| `cunhuo` | 存货 |
| `lirunzonghe` | 利润总额 |
| `shuihoulirun` | 税后利润 |
| `jinglirun` | 净利润 |
| `weifenpeilirun` | 未分配利润 |
| `meigujingzichan` | 每股净资产 |
| `baoliu2` | 保留字段（协议原值） |

---

## 1) `get_security_quotes`

### 描述

按 `(market, code)` 列表批量拉取五档快照。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `all_stock` | `list[tuple[int, str]]` / `tuple[int, str]` / `int` | 是 | 支持三种形式：`[(m,c)]`、`(m,c)`、`(m, code)` |
| `code` | `str` | 否 | 仅在 `all_stock` 传单个 `market` 时使用 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `market`, `code` | `int`, `str` | 市场与代码 |
| `price`, `last_close`, `open`, `high`, `low` | `float` | 最新/昨收/开高低 |
| `vol`, `cur_vol`, `s_vol`, `b_vol` | `int/float` | 总量、现量、内外盘相关 |
| `amount` | `float` | 成交额 |
| `servertime` | `str` | 服务器时间（格式化字符串） |
| `bid1..bid5`, `ask1..ask5` | `float` | 五档价格 |
| `bid_vol1..bid_vol5`, `ask_vol1..ask_vol5` | `int/float` | 五档挂单量 |
| `active1`, `active2` | `int` | 活跃度相关原始值 |
| `reversed_bytes0..8` | `int/tuple` | 协议保留/未完全语义化字段 |
| `reversed_bytes9` | `float` | 当前实现按“涨速”处理（`/100.0`） |

### 注意事项

- 某些非股票品种可能存在价格倍率差异（常见 `x10`）。
- 字段较多，建议先 `api.to_df(...)` 后按列裁剪。
- 拼音字段可参考上文“字段命名对照（交易语境）”。

### 样例

```python
api.get_security_quotes([(0, '000001'), (1, '600300')])
```

---

## 2) `get_security_bars`

### 描述

获取个股 K 线。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `category` | `int` | 是 | K 线周期 |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |
| `start` | `int` | 是 | 起始偏移 |
| `count` | `int` | 是 | 请求条数（单次建议 `<=800`） |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `open`, `close`, `high`, `low` | `float` | OHLC |
| `vol` | `float` | 成交量 |
| `amount` | `float` | 成交额 |
| `year`, `month`, `day`, `hour`, `minute` | `int` | 拆分时间 |
| `datetime` | `str` | 时间字符串 |

### 注意事项

- 停牌日也可能返回 K 线，通常成交量为 `0`。

### 样例

```python
api.get_security_bars(9, 0, '000001', 0, 10)
```

---

## 3) `get_security_count`

### 描述

获取指定市场证券数量。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |

### 输出

返回类型：`int`

| 值 | 类型 | 说明 |
| --- | --- | --- |
| 证券总数 | `int` | 指定市场的总证券数量 |

### 注意事项

- 北交所可用 `market=2` 查询数量。

### 样例

```python
api.get_security_count(0)
```

---

## 4) `get_security_list`

### 描述

分页获取证券列表。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `start` | `int` | 是 | 起始偏移 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `str` | 证券代码 |
| `volunit` | `int` | 交易单位 |
| `decimal_point` | `int` | 小数位数 |
| `name` | `str` | 名称（GBK 解码） |
| `pre_close` | `float` | 昨收 |

### 注意事项

- `get_security_list(2, start)` 在多数主站容易超时。
- 北交所列表建议独立数据源，行情查询仍可用 `market=2`。

### 样例

```python
api.get_security_list(1, 0)
```

---

## 5) `get_index_bars`

### 描述

获取指数 K 线。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `category` | `int` | 是 | K 线周期 |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 指数代码 |
| `start` | `int` | 是 | 起始偏移 |
| `count` | `int` | 是 | 请求条数（单次建议 `<=800`） |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `open`, `close`, `high`, `low` | `float` | OHLC |
| `vol`, `amount` | `float` | 量额 |
| `year`, `month`, `day`, `hour`, `minute`, `datetime` | `int/str` | 时间 |
| `up_count`, `down_count` | `int` | 上涨/下跌家数（指数场景） |

### 注意事项

- 相比 `get_security_bars` 多 `up_count/down_count`。

### 样例

```python
api.get_index_bars(9, 1, '000001', 0, 10)
```

---

## 6) `get_minute_time_data`

### 描述

获取当日分时数据。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `price` | `float` | 分钟价格 |
| `vol` | `int/float` | 分钟成交量 |

### 注意事项

- 分钟序列长度与交易时段和品种有关。

### 样例

```python
api.get_minute_time_data(1, '600300')
```

---

## 7) `get_history_minute_time_data`

### 描述

获取历史某日分时数据。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |
| `date` | `int` | 是 | `YYYYMMDD` |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `price` | `float` | 分钟价格 |
| `vol` | `int/float` | 分钟成交量 |

### 注意事项

- 无数据时返回空列表。

### 样例

```python
api.get_history_minute_time_data(1, '600300', 20161209)
```

---

## 8) `get_transaction_data`

### 描述

获取当日分笔成交。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |
| `start` | `int` | 是 | 起始偏移 |
| `count` | `int` | 是 | 请求条数 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `time` | `str` | 成交时间（`HH:MM`） |
| `price` | `float` | 成交价 |
| `vol` | `int/float` | 成交量 |
| `num` | `int/float` | 笔数/附加量字段 |
| `buyorsell` | `int/float` | 买卖方向标识 |

### 注意事项

- 字段语义依赖上游协议，`buyorsell` 建议按业务自行映射。

### 样例

```python
api.get_transaction_data(0, '000001', 0, 30)
```

---

## 9) `get_history_transaction_data`

### 描述

获取历史分笔成交。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |
| `start` | `int` | 是 | 起始偏移 |
| `count` | `int` | 是 | 请求条数 |
| `date` | `int` | 是 | `YYYYMMDD` |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `time` | `str` | 成交时间（`HH:MM`） |
| `price` | `float` | 成交价 |
| `vol` | `int/float` | 成交量 |
| `buyorsell` | `int/float` | 买卖方向标识 |

### 注意事项

- 与当日分笔相比，此接口返回中无 `num` 字段。

### 样例

```python
api.get_history_transaction_data(0, '000001', 0, 10, 20170209)
```

---

## 10) `get_company_info_category`

### 描述

获取公司资料目录。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | `str` | 目录名称 |
| `filename` | `str` | 文件名 |
| `start` | `int` | 起始偏移 |
| `length` | `int` | 内容长度 |

### 注意事项

- `start/length` 用于后续 `get_company_info_content` 调用。

### 样例

```python
api.get_company_info_category(0, '000001')
```

---

## 11) `get_company_info_content`

### 描述

读取公司资料正文内容。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |
| `filename` | `str` | 是 | 文件名（通常来自目录接口） |
| `start` | `int` | 是 | 起始偏移 |
| `length` | `int` | 是 | 读取长度 |

### 输出

返回类型：`str`

| 值 | 类型 | 说明 |
| --- | --- | --- |
| 正文文本 | `str` | GBK 解码后的文本 |

### 注意事项

- 内部会分段拉取并拼接，返回完整字符串。

### 样例

```python
api.get_company_info_content(0, '000001', '000001.txt', 0, 100)
```

---

## 12) `get_xdxr_info`

### 描述

获取除权除息与股本变动信息。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `year`, `month`, `day` | `int` | 日期 |
| `category` | `int` | 事件类别 |
| `name` | `str` | 类别名称 |
| `fenhong`, `peigujia`, `songzhuangu`, `peigu` | `float/None` | 分红配股相关 |
| `suogu` | `float/None` | 缩股相关 |
| `panqianliutong`, `panhouliutong` | `float/None` | 变动前后流通股 |
| `qianzongguben`, `houzongguben` | `float/None` | 变动前后总股本 |
| `fenshu`, `xingquanjia` | `float/None` | 权证相关 |

### 注意事项

- 不同 `category` 仅部分字段有值，其他字段为 `None`。
- 拼音字段可参考上文“字段命名对照（交易语境）”。

### 样例

```python
api.get_xdxr_info(1, '600300')
```

---

## 13) `get_finance_info`

### 描述

获取财务结构化数据（单标的）。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `market` | `int` | 是 | 市场代码 |
| `code` | `str` | 是 | 证券代码 |

### 输出

返回类型：`OrderedDict`

| 字段组 | 代表字段 | 说明 |
| --- | --- | --- |
| 标识字段 | `market`, `code`, `updated_date`, `ipo_date` | 基础信息 |
| 股本结构 | `liutongguben`, `zongguben`, `guojiagu`, `faqirenfarengu`, `farengu`, `bgu`, `hgu`, `zhigonggu` | 股本相关 |
| 资产负债 | `zongzichan`, `liudongzichan`, `gudingzichan`, `wuxingzichan`, `liudongfuzhai`, `changqifuzhai` | 资产负债相关 |
| 收益现金流 | `zhuyingshouru`, `zhuyinglirun`, `yingyelirun`, `touzishouyu`, `jingyingxianjinliu`, `zongxianjinliu` | 经营指标 |
| 利润类 | `lirunzonghe`, `shuihoulirun`, `jinglirun`, `weifenpeilirun` | 利润指标 |
| 其它 | `province`, `industry`, `gudongrenshu`, `meigujingzichan`, `baoliu2` | 其余字段 |

### 注意事项

- 当前实现字段总数为 37。
- 多数金额字段在实现中已做单位换算（`*10000`）。
- 字段中文语义可参考上文“字段命名对照（交易语境）”。

### 样例

```python
api.get_finance_info(0, '000001')
```

---

## 14) `get_k_data`

### 描述

日线便捷接口，内部封装多次 `get_security_bars` 后返回 DataFrame。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | `str` | 是 | 证券代码 |
| `start_date` | `str` | 是 | 起始日期（`YYYY-MM-DD`） |
| `end_date` | `str` | 是 | 结束日期（`YYYY-MM-DD`） |

### 输出

返回类型：`pandas.DataFrame`

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| `open`, `close`, `high`, `low` | `float` | OHLC |
| `vol`, `amount` | `float` | 量额 |
| `date` | `str` | 日期列 |
| `code` | `str` | 代码列 |

### 注意事项

- 返回索引为 `date`。
- 自动按代码推断市场（含北交所规则）。

### 样例

```python
api.get_k_data('000001', '2017-07-03', '2017-07-10')
```

---

## 15) `get_and_parse_block_info`

### 描述

读取并解析板块文件。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `blockfile` | `str` | 是 | 板块文件名 |

### 输出

返回类型：`list[dict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 依解析结果而定 | `dict` | 包含板块名、代码列表等信息 |

### 注意事项

- 常用文件：`block.dat`、`block_zs.dat`、`block_fg.dat`、`block_gn.dat`。

### 样例

```python
from pytdx.params import TDXParams

api.get_and_parse_block_info('block.dat')
api.get_and_parse_block_info(TDXParams.BLOCK_SZ)
```

---

## 16) `get_market_quotes_snapshot`

### 描述

对 `get_security_quotes` 的封装，支持传 `code_list` 并自动推断市场。

### 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `all_stock` | `list[tuple[int, str]]` | 否 | 直接指定 `(market, code)` 列表 |
| `code_list` | `list[str]` | 否 | 只传代码时自动推断市场 |
| `market_hint` | `int` | 否 | 返回结果按市场过滤 |

### 输出

返回类型：`list[OrderedDict]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 与 `get_security_quotes` 完全一致 | 同上 | 五档快照字段 |

### 注意事项

- `code_list` 与 `all_stock` 至少提供一个。
- 自动市场规则对 `92/4/8` 前缀代码按北交所处理。

### 样例

```python
api.get_market_quotes_snapshot(all_stock=[(2, '920088'), (1, '513350')])
api.get_market_quotes_snapshot(code_list=['920088', '513350'], market_hint=2)
```

---

## 17) `get_etf_panel_table`

### 描述

ETF 面板实验接口（抓包逆向），按分块方式拉取。

### 输入

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `panel_path` | `str` | 否 | `bi_diy/list/gxjty_etfjj101.jsn` | 面板路径 |
| `warmup_stock` | `tuple[int, str]` | 否 | `(0, '159919')` | 预热标的 |
| `chunk_size` | `int` | 否 | `30000` | 分块大小 |
| `max_chunks` | `int` | 否 | `12` | 最大分块数 |
| `focus_codes` | `list[str]` | 否 | `None` | 关注代码 |

### 输出

返回类型：`dict`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `columns` | `list` | 表头 |
| `rows` | `list` | 数据行 |
| `offsets` | `list[int]` | 已拉取 offset |
| `incomplete` | `bool` | 是否可能未拉全 |
| `focus_rows` | `dict` | 命中 `focus_codes` 的行 |
| `errors` | `list[str]` | 错误信息 |

### 注意事项

- 属于实验接口，服务端变更可能导致解析失效。
- `errors` 非空时应按失败处理。

### 样例

```python
api.get_etf_panel_table(
    panel_path='bi_diy/list/gxjty_etfjj101.jsn',
    warmup_stock=(0, '159919'),
    focus_codes=['513350', '159518', '515220'],
)
```

---

## 运行选项（非业务 API）

| 选项 | 构造参数 | 说明 |
| --- | --- | --- |
| 多线程 | `multithread=True` | 并发请求时可用 |
| 心跳 | `heartbeat=True` | 空闲保活，自动启用多线程 |
| 异常模式 | `raise_exception=True` | 失败抛 `TdxConnectionError` / `TdxFunctionCallError` |
| 自动重试 | `auto_retry=True` | 断连时按策略自动重连 |

## 调试与统计

### 调试

```bash
TDX_DEBUG=1 hqget -f 1
```

### 服务器列表

```python
from pytdx.config.hosts import hq_hosts
```

### 流量统计

```python
api.get_traffic_stats()
```
