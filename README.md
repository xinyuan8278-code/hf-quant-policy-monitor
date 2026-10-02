# 中国高频量化 · 政策与技术变化监控

微信公众号情报监控页 —— 面向个人／机构类中高频量化投资人，跟踪中国监管与交易所对高频量化业务的潜在政策与技术变化。

- **线上地址**：https://cn-hf-quant-watch.netlify.app
- **GitHub**：https://github.com/xinyuan8278-code/hf-quant-policy-monitor
- **检索渠道**：微信公众号文章（搜狗微信检索，会话预热版脚本，24 关键词矩阵）
- **更新机制**：7 天窗口 + 跨日去重（只输出「近 7 天 ∩ 未被历史推送过」的新增项）
- **五个维度**：交易所规则调整 / 监管动向与新规 / 技术与交易接入 / 机房搬迁与线路 / 外资高频与做市
- **数据更新日期**：2026-10-02

## 文件

| 文件 | 说明 |
|---|---|
| `index.html` | 监控页（纯静态，含分类筛选与条目展开） |
| `data.js` | 数据（`REPORT_META` + `ARTICLES`），更新时只改此文件 |
| `_headers` | Netlify 缓存头（`data.js` 禁用缓存，保证更新即时可见） |
| `deploy_netlify.py` | Netlify API 直连部署脚本（增量上传） |
| `push_github.py` | 通过 GitHub API 建仓并推送（可选） |

## 部署

```bash
PY="C:/Users/Lenovo/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
$PY deploy_netlify.py --site-name cn-hf-quant-watch
```

凭据：`.netlify-token`（已 gitignore），或环境变量 `NETLIFY_AUTH_TOKEN`。

> 注：Netlify 站点名若含 `policy` 会被判为非法子域（422 `subdomain is not valid`），故实际站点名为 `cn-hf-quant-watch`。

## 口径与限制

1. 搜狗微信**不支持按时间排序/过滤**，时间窗口只能本地二次过滤；24 小时窗口命中率≈0，故取 7 天窗口 + 跨日去重。
2. **阅读量与「在看」不可得**：搜狗不返回阅读量；在看属微信客户端本地数据。故本页未按热度排序。
3. **原文正文未抓取**：搜狗跳转链接触发反爬。`note` = 检索摘要 + 原留档注记。
4. 官方与非官方信息均纳入，每条标注性质（官方公告 / 自媒体·非官方 / 推测·传闻 / 厂商宣传 / 参考资料），忠于源内容，未扩写。
5. 涉及规则生效日期者已标注前瞻性，实际以交易所与监管机构正式公告为准。

---

本页仅供内部研究参考，不构成投资建议。
