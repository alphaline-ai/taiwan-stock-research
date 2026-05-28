"""
stocks.py — Single source of truth for the tracked universe.

Layer convention:
  0 — Equipment (對照組)
  1 — Shortage-effect Taiwan 2nd-tier
  2 — HBM / DRAM majors (Korea + Micron)
  3 — Taiwan DRAM
"""

STOCKS: dict[str, dict] = {
    # Layer 0 — Equipment
    "ASML":      {"name": "ASML",                "layer": 0, "category": "equipment"},
    "AMAT":      {"name": "Applied Materials",   "layer": 0, "category": "equipment"},
    "LRCX":      {"name": "Lam Research",        "layer": 0, "category": "equipment"},
    "KLAC":      {"name": "KLA",                 "layer": 0, "category": "equipment"},

    # Layer 1 — Taiwan shortage-effect
    "2330.TW":   {"name": "TSMC",                "layer": 1, "category": "foundry"},
    "2454.TW":   {"name": "MediaTek",            "layer": 1, "category": "ic-design"},
    "2303.TW":   {"name": "UMC",                 "layer": 1, "category": "foundry"},
    "3711.TW":   {"name": "ASE",                 "layer": 1, "category": "packaging"},
    "3037.TW":   {"name": "Unimicron",           "layer": 1, "category": "pcb"},
    "2383.TW":   {"name": "Elite (台光)",         "layer": 1, "category": "ccl"},
    "3443.TW":   {"name": "GUC (創意)",           "layer": 1, "category": "asic"},

    # Layer 2 — HBM / DRAM majors
    "000660.KS": {"name": "SK Hynix",            "layer": 2, "category": "hbm"},
    "005930.KS": {"name": "Samsung",             "layer": 2, "category": "hbm"},
    "MU":        {"name": "Micron",              "layer": 2, "category": "hbm"},

    # Layer 3 — Taiwan DRAM
    "2409.TW":   {"name": "Nanya (南亞科)",       "layer": 3, "category": "taiwan-dram"},
    "2344.TW":   {"name": "Winbond (華邦電)",     "layer": 3, "category": "taiwan-dram"},
}

EQUIPMENT_TICKERS   = [t for t, m in STOCKS.items() if m["layer"] == 0]
SHORTAGE_TICKERS    = [t for t, m in STOCKS.items() if m["layer"] == 1]
DRAM_TICKERS        = [t for t, m in STOCKS.items() if m["layer"] == 2]
TAIWAN_DRAM_TICKERS = [t for t, m in STOCKS.items() if m["layer"] == 3]

LAYER_LABELS = {
    0: "Equipment",
    1: "Shortage / Taiwan 2nd-tier",
    2: "HBM / DRAM Majors",
    3: "Taiwan DRAM",
}
