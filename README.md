# Taiwan Stock Research

每週自動更新的台股 + 國際半導體 valuation 快照。

**Live dashboard:** https://howardpen9.github.io/taiwan-stock-research/

## 追蹤宇宙（17 檔）

| Layer | 主題 | 代表 |
|-------|------|------|
| 0 | 半導體設備 | ASML / AMAT / LRCX / KLAC |
| 1 | 短缺效應台廠 | TSMC / MediaTek / UMC / ASE / Unimicron / Elite / GUC |
| 2 | HBM / DRAM 大廠 | SK Hynix / Samsung / Micron |
| 3 | 台灣 DRAM | Nanya / Winbond |

核心觀察：**設備 ÷ DRAM PE Ratio** 收斂 = DRAM catch-up 訊號。

## 本地執行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 首次：回填 52 週價格歷史（PE 留 None）
python scripts/fetch_data.py --bootstrap

# 加當週快照（含 PE）
python scripts/fetch_data.py

# 渲染報告
python scripts/generate_report.py
open output/index.html
```

## 自動化

`.github/workflows/weekly.yml` 在每週一 UTC 01:00（台北 09:00）執行：

1. `python scripts/fetch_data.py`
2. `python scripts/generate_report.py`
3. commit `data/history.json` + `output/*` 回 `main`
4. GitHub Pages 自動發布到 `/output`

可在 Actions tab 用 `workflow_dispatch` 手動觸發。

## 結構

```
scripts/
  stocks.py            # 清單 single source of truth
  fetch_data.py        # 抓資料（含 --bootstrap）
  generate_report.py   # 渲染 HTML + summary.json
templates/
  report.html.j2       # Jinja2 模板（深色主題、inline CSS）
data/
  history.json         # 累積快照（git tracked）
output/
  index.html           # GH Pages serve
  summary.json         # 機器可讀摘要
```

## Roadmap

- v0 ✅ — fetch + table + signals + GH Pages
- v1 — Chart.js 時序圖（設備 vs DRAM PE）
- v1 — 產業內 percentile 排名（仿 MoatMap.ai）
- v1 — TWSE 月營收抓取（mops.twse.com.tw）
- v1 — Telegram / Line 推播

---

*For research only. Not investment advice. Data via [yfinance](https://github.com/ranaroussi/yfinance) / Yahoo Finance.*
