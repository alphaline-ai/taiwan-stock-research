#!/usr/bin/env python3
"""
generate_report.py — render output/index.html + output/summary.json from history.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "docs"
HISTORY_FILE = DATA_DIR / "history.json"

sys.path.insert(0, str(ROOT / "scripts"))
from stocks import (  # noqa: E402
    STOCKS,
    EQUIPMENT_TICKERS,
    DRAM_TICKERS,
    TAIWAN_DRAM_TICKERS,
)


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        print("ERROR: data/history.json not found. Run scripts/fetch_data.py first.",
              file=sys.stderr)
        sys.exit(1)
    with open(HISTORY_FILE) as f:
        return json.load(f)


def safe_avg(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def latest_weekly_snapshot(history: list[dict]) -> dict:
    """Return the most recent snapshot that has PE data (i.e. kind='weekly')."""
    for snap in reversed(history):
        if snap.get("kind") == "weekly" or any(
            p.get("forward_pe") for p in snap.get("prices", {}).values()
        ):
            return snap
    return history[-1] if history else {}


def build_context(history: list[dict]) -> dict:
    latest = latest_weekly_snapshot(history)
    prices = latest.get("prices", {})

    # --- Summary cards ---
    equip_fpe   = safe_avg([prices.get(t, {}).get("forward_pe") for t in EQUIPMENT_TICKERS])
    dram_fpe    = safe_avg([prices.get(t, {}).get("forward_pe") for t in DRAM_TICKERS])
    tw_dram_fpe = safe_avg([prices.get(t, {}).get("forward_pe") for t in TAIWAN_DRAM_TICKERS])
    pe_ratio    = (equip_fpe / dram_fpe) if (equip_fpe and dram_fpe) else None

    # --- Valuation table ---
    valuation_rows = []
    for ticker, meta in STOCKS.items():
        p = prices.get(ticker, {})
        valuation_rows.append({
            "ticker":       ticker,
            "name":         meta["name"],
            "layer":        meta["layer"],
            "category":     meta["category"],
            "price":        p.get("price"),
            "forward_pe":   p.get("forward_pe"),
            "trailing_pe":  p.get("trailing_pe"),
            "market_cap_b": round(p["market_cap"] / 1e9, 1) if p.get("market_cap") else None,
        })
    valuation_rows.sort(key=lambda r: (r["layer"], r["ticker"]))

    # --- Signals ---
    signals = build_signals(history, prices, equip_fpe, dram_fpe, tw_dram_fpe, pe_ratio)

    return {
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "data_as_of":  latest.get("snapshot_date", "—"),
        "total_stocks": len(prices),
        "summary_cards": {
            "equip_fpe":   equip_fpe,
            "dram_fpe":    dram_fpe,
            "tw_dram_fpe": tw_dram_fpe,
            "pe_ratio":    pe_ratio,
        },
        "valuation_rows": valuation_rows,
        "signals":        signals,
    }


def build_signals(history, prices, equip_fpe, dram_fpe, tw_dram_fpe, pe_ratio) -> list[str]:
    signals: list[str] = []

    # Signal 1: PE ratio (equipment / DRAM) — compare to previous weekly snapshot
    weekly_snaps = [s for s in history if s.get("kind") == "weekly"]
    if pe_ratio and len(weekly_snaps) >= 2:
        prev_prices = weekly_snaps[-2].get("prices", {})
        prev_equip = safe_avg([prev_prices.get(t, {}).get("forward_pe") for t in EQUIPMENT_TICKERS])
        prev_dram  = safe_avg([prev_prices.get(t, {}).get("forward_pe") for t in DRAM_TICKERS])
        if prev_equip and prev_dram:
            prev_ratio = prev_equip / prev_dram
            delta = pe_ratio - prev_ratio
            if abs(delta) >= 0.3:
                arrow = "↑" if delta > 0 else "↓"
                signals.append(
                    f"📊 設備/DRAM PE Ratio {arrow} {pe_ratio:.2f}x "
                    f"(週變動 {delta:+.2f})"
                )

    # Signal 2: Taiwan DRAM discount vs global DRAM majors
    if tw_dram_fpe and dram_fpe and dram_fpe > 0:
        discount = (dram_fpe - tw_dram_fpe) / dram_fpe * 100
        if discount > 25:
            signals.append(
                f"🟡 台灣 DRAM 折價 {discount:.0f}% "
                f"(TW {tw_dram_fpe:.1f}x vs 全球 {dram_fpe:.1f}x)"
            )
        elif discount < -10:
            signals.append(
                f"🟠 台灣 DRAM 溢價 {-discount:.0f}%（罕見訊號）"
            )

    # Signal 3: TSMC price momentum (1w change)
    if len(weekly_snaps) >= 2:
        tsmc_now = prices.get("2330.TW", {}).get("price")
        tsmc_prev = weekly_snaps[-2].get("prices", {}).get("2330.TW", {}).get("price")
        if tsmc_now and tsmc_prev:
            pct = (tsmc_now - tsmc_prev) / tsmc_prev * 100
            if abs(pct) >= 3:
                arrow = "↑" if pct > 0 else "↓"
                signals.append(f"💎 TSMC 週漲跌 {arrow} {pct:+.1f}% (NT${tsmc_now:.0f})")

    # Always-on context
    n_with_pe = sum(1 for v in prices.values() if v.get("forward_pe"))
    signals.append(
        f"📥 本週成功取得 {len(prices)} 檔即時報價，其中 {n_with_pe} 檔有 Forward PE 數據"
    )

    return signals


def main() -> None:
    print("=== generate_report ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()
    context = build_context(history)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("report.html.j2")
    html = template.render(**context)

    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")

    summary = {k: v for k, v in context.items() if k != "valuation_rows"}
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    pe_ratio = context["summary_cards"]["pe_ratio"]
    print(f"✅ output/index.html  ({len(html):,} bytes)")
    print(f"   output/summary.json")
    print(f"   stocks: {context['total_stocks']}  ·  "
          f"PE ratio: {pe_ratio:.2f}x" if pe_ratio else
          f"   stocks: {context['total_stocks']}  ·  PE ratio: —")
    print(f"   signals: {len(context['signals'])}")


if __name__ == "__main__":
    main()
