#!/usr/bin/env python3
"""
fetch_data.py — Fetch one weekly snapshot (default) or bootstrap 52w of prices.

Default:
    python scripts/fetch_data.py
    → append one snapshot with full info (price + PE + market cap + EPS) for every ticker

Bootstrap:
    python scripts/fetch_data.py --bootstrap
    → backfill 52 weeks of price-only snapshots using yf.Ticker.history()
      PE columns left None (yfinance does not provide historical fundamentals).
      Idempotent: skips if data/history.json already has bootstrap snapshots.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"

sys.path.insert(0, str(ROOT / "scripts"))
from stocks import STOCKS  # noqa: E402


def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def save_history(history: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def fetch_live_quote(ticker: str) -> dict | None:
    """Fetch current price + fundamentals for one ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            return None

        forward_pe = info.get("forwardPE")
        # Fallback: derive forward_pe from price / forwardEps (Taiwan tickers often miss forwardPE)
        if forward_pe is None:
            fwd_eps = info.get("forwardEps")
            if fwd_eps and fwd_eps > 0:
                forward_pe = price / fwd_eps

        return {
            "price": round(float(price), 2),
            "currency": info.get("currency"),
            "market_cap": info.get("marketCap"),
            "forward_pe": round(float(forward_pe), 2) if forward_pe else None,
            "trailing_pe": round(float(info["trailingPE"]), 2) if info.get("trailingPE") else None,
            "peg_ratio": info.get("pegRatio"),
            "eps_ttm": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "revenue_growth": info.get("revenueGrowth"),
        }
    except Exception as e:
        print(f"  [SKIP] {ticker}: {e}", file=sys.stderr)
        return None


def append_weekly_snapshot() -> None:
    print("=== fetch_data: weekly snapshot ===")
    history = load_history()

    snapshot = {
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": "weekly",
        "prices": {},
    }

    for ticker in STOCKS:
        meta = STOCKS[ticker]
        print(f"  fetching {ticker:<10} ({meta['name']})")
        quote = fetch_live_quote(ticker)
        if quote:
            snapshot["prices"][ticker] = quote

    history.append(snapshot)
    # Cap at ~3 years of weekly snapshots
    if len(history) > 200:
        history = history[-200:]
    save_history(history)

    n_with_pe = sum(1 for v in snapshot["prices"].values() if v.get("forward_pe"))
    print(f"\n✅ Snapshot saved: {len(snapshot['prices'])}/{len(STOCKS)} stocks "
          f"({n_with_pe} with forward PE)")
    print(f"   History total: {len(history)} snapshots")


def bootstrap_history() -> None:
    """Backfill 52 weeks of price-only snapshots."""
    print("=== fetch_data: bootstrap (52w weekly history) ===")
    history = load_history()

    if any(s.get("kind") == "bootstrap" for s in history):
        print("⚠️  History already contains bootstrap snapshots. Skipping.")
        print("    (delete data/history.json to re-bootstrap)")
        return

    # For each ticker, pull 1y/1wk history
    per_ticker_history: dict[str, dict[str, float]] = {}  # ticker → {date_str: close}
    for ticker in STOCKS:
        meta = STOCKS[ticker]
        print(f"  fetching {ticker:<10} ({meta['name']}) 1y/1wk...")
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1wk")
            if df.empty:
                print(f"    [SKIP] empty dataframe")
                continue
            per_ticker_history[ticker] = {
                idx.strftime("%Y-%m-%d"): round(float(row["Close"]), 2)
                for idx, row in df.iterrows()
                if row["Close"] and row["Close"] > 0
            }
        except Exception as e:
            print(f"    [SKIP] {e}", file=sys.stderr)

    # Pivot to per-date snapshots (union of all dates seen)
    all_dates = sorted({d for hist in per_ticker_history.values() for d in hist})
    print(f"\n  pivoting to {len(all_dates)} weekly snapshots...")

    new_snapshots: list[dict] = []
    for date_str in all_dates:
        snap = {
            "snapshot_date": date_str,
            "timestamp": f"{date_str}T00:00:00+00:00",
            "kind": "bootstrap",
            "prices": {},
        }
        for ticker, hist in per_ticker_history.items():
            if date_str in hist:
                snap["prices"][ticker] = {
                    "price": hist[date_str],
                    "currency": None,
                    "market_cap": None,
                    "forward_pe": None,
                    "trailing_pe": None,
                    "peg_ratio": None,
                    "eps_ttm": None,
                    "eps_forward": None,
                    "revenue_growth": None,
                }
        new_snapshots.append(snap)

    # Prepend bootstrap snapshots before any existing data
    history = new_snapshots + history
    save_history(history)

    print(f"\n✅ Bootstrap complete: {len(new_snapshots)} weekly snapshots")
    print(f"   Tickers with data: {len(per_ticker_history)}/{len(STOCKS)}")
    print(f"   Earliest: {all_dates[0] if all_dates else 'N/A'}")
    print(f"   Latest:   {all_dates[-1] if all_dates else 'N/A'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", action="store_true",
                        help="Backfill 52 weeks of price-only history then exit")
    args = parser.parse_args()

    if args.bootstrap:
        bootstrap_history()
    else:
        append_weekly_snapshot()


if __name__ == "__main__":
    main()
