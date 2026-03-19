# Known Issues

## 2026-03-19: `get_security_list(2, 0)` 在主流行情节点超时

- 影响范围：`pytdx.hq.TdxHq_API.get_security_list(market=2, start=...)`
- 复现条件：
  - 可正常连接 `7709` 行情主站
  - `get_security_count(2)` 返回 `323`
  - 调用 `get_security_list(2, 0)` 约 3 秒后超时（`TimeoutError`，`raise_exception=False` 时返回 `None`）
- 观测结论：
  - 在多个主站（含 `jstdx.gtjas.com`、`shtdx.gtjas.com`、`sztdx.gtjas.com` 及若干 IP）现象一致
  - 说明该命令在 `market=2` 上大概率是服务端未开放/未实现，不是单一节点问题
- 临时规避：
  - 北交所行情查询可继续使用 `market=2`（如 `get_security_quotes/get_security_bars`）
  - 北交所代码列表请先使用其他数据源

