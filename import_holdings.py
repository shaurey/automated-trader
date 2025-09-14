"""Import holdings from a brokerage CSV into the SQLite database.

Features:
- Auto-detect common column names (Symbol/Ticker, Quantity/Shares, CostBasis/AvgCost, Account, Open/Purchase Date, Type/AssetType)
- Skip option positions (basic pattern + type hints)
- Include only stocks & ETFs (instrument_type set accordingly)
- Upsert instruments (do not overwrite existing style_category)
- Insert holdings rows (optionally merge or skip duplicates per account+ticker)
- Compute per-share cost if total cost provided (flag --cost-is-total)

Usage (PowerShell examples):
  python .\import_holdings.py --db at_data.sqlite --csv "C:\\Users\\rohitg\\Downloads\\Portfolio_Positions_Sep-14-2025.csv"
  python .\import_holdings.py --db at_data.sqlite --csv "...csv" --dry-run --verbose
  python .\import_holdings.py --db at_data.sqlite --csv "...csv" --merge-existing

Optional flags see --help.
"""
from __future__ import annotations
import argparse, csv, datetime, os, re, sqlite3, sys
from typing import Dict, List, Optional, Tuple

OPTION_PATTERNS = [
    re.compile(r".+\s+\d{2}[A-Z]{3}\d{2}\s+\d+(\.\d+)?[CP]", re.IGNORECASE),  # OCC style line
    re.compile(r".*\d{6}[CP]$", re.IGNORECASE),  # trailing YYMMDD + C/P
]
TYPE_HINT_COLUMNS = ["Type", "AssetType", "Asset Class", "SecurityType", "Security Type", "InstrumentType"]

# ---------- Helpers ----------

def detect_column(header: List[str], candidates: List[str]) -> Optional[str]:
    lower_map = {h.lower(): h for h in header}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    # substring fallback
    for h in header:
        hl = h.lower()
        if any(cand.lower() in hl for cand in candidates):
            return h
    return None

def normalize_symbol(sym: str) -> str:
    s = sym.strip().upper().replace(".", "-")
    # Map BRK B -> BRK-B, etc.
    if " " in s and len(s.split()) == 2 and len(s.split()[1]) == 1:
        parts = s.split()
        s = parts[0] + "-" + parts[1]
    return s

def is_option(symbol: str, row: Dict[str, str]) -> bool:
    s = symbol.upper().strip()
    # Share class allowance already normalized; treat other spaces or '/' as option-like
    if (" " in s or "/" in s) and not re.match(r"^[A-Z]+-[A-Z]$", s):
        return True
    for pat in OPTION_PATTERNS:
        if pat.match(s):
            return True
    for col in TYPE_HINT_COLUMNS:
        v = row.get(col)
        if v and "OPTION" in v.upper():
            return True
    return False

# ---------- Import Logic ----------

def parse_args():
    ap = argparse.ArgumentParser(description="Import stock/ETF holdings into SQLite")
    ap.add_argument("--db", default="at_data.sqlite", help="SQLite DB path")
    ap.add_argument("--csv", required=True, help="Input CSV path")
    ap.add_argument("--symbol-col")
    ap.add_argument("--quantity-col")
    ap.add_argument("--cost-col", help="Per-share cost column (or total if --cost-is-total)")
    ap.add_argument("--account-col")
    ap.add_argument("--date-col")
    ap.add_argument("--etf-col", help="Column indicating ETF (value contains 'ETF')")
    ap.add_argument("--etf-list", help="Comma separated tickers treated as ETFs")
    ap.add_argument("--cost-is-total", action="store_true", help="Interpret cost column as total dollars, derive per-share")
    ap.add_argument("--default-account", default="MAIN")
    ap.add_argument("--merge-existing", action="store_true", help="Merge into existing position (weighted avg cost)")
    ap.add_argument("--skip-if-exists", action="store_true", help="Skip insert if holdings row exists for account+ticker")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()

def load_csv(path: str) -> Tuple[List[Dict[str,str]], List[str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        rows = list(rdr)
    return rows, (list(rows[0].keys()) if rows else [])

def ensure_tables(cur: sqlite3.Cursor):
    # Minimal existence check (schema already established by db.py)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instruments'")
    if not cur.fetchone():
        raise SystemExit("instruments table missing; run schema initialization first.")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='holdings'")
    if not cur.fetchone():
        raise SystemExit("holdings table missing; run schema initialization first.")

def main():
    args = parse_args()
    if not os.path.exists(args.csv):
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 2
    rows, header = load_csv(args.csv)
    if not rows:
        print("CSV empty")
        return 1

    symbol_col = args.symbol_col or detect_column(header, ["Symbol", "Ticker", "Security", "Instrument"])
    qty_col = args.quantity_col or detect_column(header, ["Quantity", "Qty", "Shares", "Position", "Units"])
    cost_col = args.cost_col or detect_column(header, ["CostBasis", "AvgCost", "AverageCost", "Cost", "Avg Price"])
    acct_col = args.account_col or detect_column(header, ["Account", "Acct", "Portfolio"])
    date_col = args.date_col or detect_column(header, ["OpenDate", "Opened", "PurchaseDate", "Date Acquired"])
    etf_col = args.etf_col or detect_column(header, ["AssetType", "Type", "Asset Class", "SecurityType"])

    if not symbol_col or not qty_col:
        print("Missing required symbol / quantity columns.")
        return 1

    etf_manual = set()
    if args.etf_list:
        etf_manual = {normalize_symbol(s) for s in args.etf_list.split(',') if s.strip()}

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    ensure_tables(cur)

    # Preload holdings if merging / skipping
    existing: Dict[Tuple[str,str], Tuple[float, Optional[float]]] = {}
    if args.merge_existing or args.skip_if_exists:
        for acct, tic, qty, cb in cur.execute("SELECT account,ticker,quantity,cost_basis FROM holdings"):
            existing[(acct, tic)] = (qty, cb)

    inserted_instruments = 0
    holdings_updates = 0
    skipped_options = 0
    skipped_existing = 0

    for i, row in enumerate(rows, 1):
        raw_sym = (row.get(symbol_col) or '').strip()
        if not raw_sym:
            continue
        sym = normalize_symbol(raw_sym)
        if is_option(sym, row):
            skipped_options += 1
            if args.verbose:
                print(f"[skip option] {sym}")
            continue
        # quantity
        try:
            qty_val = float(str(row.get(qty_col, '')).replace(',', ''))
        except Exception:
            if args.verbose:
                print(f"[skip bad qty] {sym} -> {row.get(qty_col)}")
            continue
        if qty_val == 0:
            continue

        # account
        account = (row.get(acct_col) or args.default_account).strip() if acct_col else args.default_account

        # cost basis per share
        cost_basis = None
        if cost_col:
            raw_cost = row.get(cost_col)
            if raw_cost:
                try:
                    val = float(str(raw_cost).replace(',', ''))
                    cost_basis = (val / qty_val) if args.cost_is_total and qty_val != 0 else val
                except Exception:
                    pass

        # date
        opened_at = None
        if date_col:
            dval = row.get(date_col)
            if dval:
                opened_at = dval.strip()
        if not opened_at:
            opened_at = datetime.datetime.utcnow().strftime('%Y-%m-%d')

        # instrument type
        inst_type = 'stock'
        etf_hint = (row.get(etf_col) or '').upper() if etf_col else ''
        if 'ETF' in etf_hint or sym in etf_manual:
            inst_type = 'etf'

        # Upsert instrument (don't overwrite existing style)
        cur.execute("SELECT ticker FROM instruments WHERE ticker=?", (sym,))
        if not cur.fetchone():
            if not args.dry_run:
                cur.execute("INSERT INTO instruments(ticker,instrument_type,updated_at) VALUES(?,?,datetime('now'))", (sym, inst_type))
            inserted_instruments += 1
        else:
            if not args.dry_run:
                cur.execute("UPDATE instruments SET instrument_type=COALESCE(instrument_type, ?) WHERE ticker=?", (inst_type, sym))

        key = (account, sym)
        if key in existing:
            if args.skip_if_exists:
                skipped_existing += 1
                continue
            if args.merge_existing:
                prev_qty, prev_cb = existing[key]
                new_qty = prev_qty + qty_val
                new_cb = prev_cb
                if cost_basis is not None and prev_cb is not None and new_qty != 0:
                    # weighted average cost
                    try:
                        new_cb = (prev_qty * prev_cb + qty_val * cost_basis) / new_qty
                    except Exception:
                        pass
                elif cost_basis is not None and prev_cb is None:
                    new_cb = cost_basis
                if not args.dry_run:
                    cur.execute(
                        "UPDATE holdings SET quantity=?, cost_basis=?, last_update=datetime('now') WHERE account=? AND ticker=?",
                        (new_qty, new_cb, account, sym),
                    )
                existing[key] = (new_qty, new_cb)
                holdings_updates += 1
                continue

        if not args.dry_run:
            cur.execute(
                """INSERT INTO holdings(account,subaccount,ticker,quantity,cost_basis,opened_at,last_update,lot_tag,notes)
                    VALUES(?,?,?,?,?,?,datetime('now'),NULL,NULL)""",
                (account, None, sym, qty_val, cost_basis, opened_at),
            )
        existing[key] = (qty_val, cost_basis)
        holdings_updates += 1

        if args.verbose and i % 50 == 0:
            print(f"Processed {i} rows...")

    if not args.dry_run:
        con.commit()

    print(f"Holdings inserted/updated: {holdings_updates}")
    print(f"New instruments inserted: {inserted_instruments}")
    print(f"Skipped option rows: {skipped_options}")
    if args.merge_existing:
        print("Mode: merge_existing")
    if args.skip_if_exists:
        print(f"Skipped existing duplicates: {skipped_existing}")
    if args.dry_run:
        print("Dry-run (no DB changes)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
