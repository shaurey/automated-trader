"""SQLite persistence layer for strategy runs, holdings, and instrument metadata.

Schema history:
v1: Base tables (holdings had instrument_type, style_category, currency; separate strategy_params)
v2: Added strategy_code to strategy_result
v3: Added params_json to strategy_run (merged former strategy_params)
v4: Introduced instruments table; moved instrument_type, style_category, currency from holdings to instruments

Current (v4):
 - schema_meta(key,value)
 - instruments(ticker PK, instrument_type, style_category, sector, industry, country, currency, active, updated_at, notes)
 - holdings(holding_id PK, account, subaccount, ticker, quantity, cost_basis, opened_at, last_update, lot_tag, notes)
 - strategy_run(run_id PK, strategy_code, version, params_hash, params_json, started_at, completed_at, universe_source, universe_size, min_score, exit_status, duration_ms)
 - strategy_result(run_id+ticker PK, strategy_code, ticker, passed, score, classification, reasons, metrics_json, created_at)

Usage pattern:
    from db import Database
    with Database(db_path) as db:
        run_id = db.start_run(...)
        db.log_result(run_id, ticker, passed, score, classification, reasons, metrics_dict)
        db.finalize_run(run_id)

All timestamps stored as UTC ISO8601 with trailing 'Z'.
"""
from __future__ import annotations
import sqlite3, json, uuid, hashlib, os, datetime
from typing import Dict, Any, Optional

SCHEMA_VERSION = "4"

DDL_STATEMENTS = [
        # schema_meta
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """,
        # instruments (new in v4 baseline)
        """
        CREATE TABLE IF NOT EXISTS instruments (
            ticker          TEXT PRIMARY KEY,
            instrument_type TEXT NOT NULL DEFAULT 'stock',
            style_category  TEXT,
            sector          TEXT,
            industry        TEXT,
            country         TEXT,
            currency        TEXT DEFAULT 'USD',
            active          INTEGER NOT NULL DEFAULT 1,
            updated_at      TEXT,
            notes           TEXT
        );
        """,
        "CREATE INDEX IF NOT EXISTS ix_instruments_type ON instruments(instrument_type);",
        "CREATE INDEX IF NOT EXISTS ix_instruments_style ON instruments(style_category);",
        # holdings (instrument_type/style_category/currency removed)
        """
        CREATE TABLE IF NOT EXISTS holdings (
            holding_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            account      TEXT NOT NULL,
            subaccount   TEXT,
            ticker       TEXT NOT NULL,
            quantity     REAL NOT NULL,
            cost_basis   REAL,
            opened_at    TEXT,
            last_update  TEXT,
            lot_tag      TEXT,
            notes        TEXT
        );
        """,
        "CREATE INDEX IF NOT EXISTS ix_holdings_account ON holdings(account);",
        "CREATE INDEX IF NOT EXISTS ix_holdings_ticker ON holdings(ticker);",
        # strategy_run
        """
        CREATE TABLE IF NOT EXISTS strategy_run (
                run_id          TEXT PRIMARY KEY,
                strategy_code   TEXT NOT NULL,
                version         TEXT NOT NULL,
                params_hash     TEXT NOT NULL,
                params_json     TEXT NOT NULL,
                started_at      TEXT NOT NULL,
                completed_at    TEXT,
                universe_source TEXT,
                universe_size   INTEGER,
                min_score       INTEGER,
                exit_status     TEXT,
                duration_ms     INTEGER
        );
        """,
        "CREATE INDEX IF NOT EXISTS ix_run_strategy_started ON strategy_run(strategy_code, started_at);",
        "CREATE INDEX IF NOT EXISTS ix_run_params ON strategy_run(strategy_code, params_hash);",
        # strategy_result
        """
        CREATE TABLE IF NOT EXISTS strategy_result (
                run_id         TEXT NOT NULL REFERENCES strategy_run(run_id) ON DELETE CASCADE,
                strategy_code  TEXT NOT NULL,
                ticker         TEXT NOT NULL,
                passed         INTEGER NOT NULL,
                score          REAL,
                classification TEXT,
                reasons        TEXT,
                metrics_json   TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                PRIMARY KEY (run_id, ticker)
        );
        """,
        "CREATE INDEX IF NOT EXISTS ix_result_ticker ON strategy_result(ticker);",
        "CREATE INDEX IF NOT EXISTS ix_result_score ON strategy_result(score);",
        "CREATE INDEX IF NOT EXISTS ix_result_class ON strategy_result(classification);",
        "CREATE INDEX IF NOT EXISTS ix_result_strategy ON strategy_result(strategy_code);",
]

class Database:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

    def connect(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.path)
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.ensure_schema()

    def ensure_schema(self):
        cur = self.conn.cursor()
        for stmt in DDL_STATEMENTS:
            cur.executescript(stmt)
        # Determine current version
        cur.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        row = cur.fetchone()
        current_version = row[0] if row else "0"

        def column_exists(table: str, column: str) -> bool:
            try:
                cur.execute(f"PRAGMA table_info({table})")
                return any(r[1] == column for r in cur.fetchall())
            except Exception:
                return False

        # v1 -> v2
        if current_version in ("0", "1"):
            if not column_exists("strategy_result", "strategy_code"):
                try:
                    cur.execute("ALTER TABLE strategy_result ADD COLUMN strategy_code TEXT")
                    cur.execute(
                        """
                        UPDATE strategy_result
                           SET strategy_code = (
                             SELECT sr.strategy_code FROM strategy_run sr WHERE sr.run_id = strategy_result.run_id
                           )
                         WHERE strategy_code IS NULL OR strategy_code='';
                        """
                    )
                except Exception as e:
                    print(f"[DB] v1->v2 add strategy_code failed: {e}")
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS ix_result_strategy ON strategy_result(strategy_code)")
            except Exception:
                pass
            current_version = "2"

        # v2 -> v3
        if current_version == "2":
            if not column_exists("strategy_run", "params_json"):
                try:
                    cur.execute("ALTER TABLE strategy_run ADD COLUMN params_json TEXT")
                except Exception as e:
                    print(f"[DB] v2->v3 add params_json failed: {e}")
            try:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strategy_params'")
                if cur.fetchone():
                    cur.execute(
                        """
                        UPDATE strategy_run SET params_json = (
                          SELECT raw_json FROM strategy_params sp WHERE sp.params_hash = strategy_run.params_hash AND sp.strategy_code = strategy_run.strategy_code
                        ) WHERE (params_json IS NULL OR params_json='');
                        """
                    )
            except Exception as e:
                print(f"[DB] v2->v3 backfill params_json failed: {e}")
            try:
                cur.execute("DROP TABLE IF EXISTS strategy_params")
            except Exception:
                pass
            current_version = "3"

        # v3 -> v4 (add instruments; remove columns from holdings)
        if current_version == "3":
            # if legacy holdings has instrument_type / style_category / currency then migrate
            cur.execute("PRAGMA table_info(holdings)")
            legacy_cols = [r[1] for r in cur.fetchall()]
            needs_rebuild = any(c in legacy_cols for c in ("instrument_type", "style_category", "currency"))
            if needs_rebuild:
                # Populate instruments from distinct holdings
                it_expr = "instrument_type" if "instrument_type" in legacy_cols else "'stock' AS instrument_type"
                sc_expr = "style_category" if "style_category" in legacy_cols else "NULL AS style_category"
                cur_expr = "currency" if "currency" in legacy_cols else "'USD' AS currency"
                try:
                    cur.execute(f"""
                        INSERT OR IGNORE INTO instruments(ticker, instrument_type, style_category, currency, updated_at)
                        SELECT DISTINCT ticker, {it_expr}, {sc_expr}, {cur_expr}, datetime('now')
                          FROM holdings
                         WHERE ticker IS NOT NULL;
                    """)
                except Exception as e:
                    print(f"[DB] v3->v4 populate instruments failed: {e}")
                # Rebuild holdings sans removed columns
                try:
                    cur.execute("""
                        CREATE TABLE holdings_new (
                          holding_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                          account      TEXT NOT NULL,
                          subaccount   TEXT,
                          ticker       TEXT NOT NULL,
                          quantity     REAL NOT NULL,
                          cost_basis   REAL,
                          opened_at    TEXT,
                          last_update  TEXT,
                          lot_tag      TEXT,
                          notes        TEXT
                        );
                    """)
                    # Prepare select list preserving data
                    sel_cols = []
                    for col in ("holding_id","account","subaccount","ticker","quantity","cost_basis","opened_at","last_update","lot_tag","notes"):
                        if col in legacy_cols:
                            sel_cols.append(col)
                        else:
                            sel_cols.append(f"NULL AS {col}")
                    cur.execute(f"INSERT INTO holdings_new(holding_id,account,subaccount,ticker,quantity,cost_basis,opened_at,last_update,lot_tag,notes) SELECT {','.join(sel_cols)} FROM holdings;")
                    cur.execute("DROP TABLE holdings;")
                    cur.execute("ALTER TABLE holdings_new RENAME TO holdings;")
                    cur.execute("CREATE INDEX IF NOT EXISTS ix_holdings_account ON holdings(account);")
                    cur.execute("CREATE INDEX IF NOT EXISTS ix_holdings_ticker ON holdings(ticker);")
                except Exception as e:
                    print(f"[DB] v3->v4 rebuild holdings failed: {e}")
            current_version = "4"

        cur.execute("""
            INSERT INTO schema_meta(key,value) VALUES('schema_version',?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (SCHEMA_VERSION,))
        self.conn.commit()

    @staticmethod
    def _now_iso() -> str:
        return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    @staticmethod
    def hash_params(params: Dict[str, Any]) -> str:
        try:
            normalized = json.dumps(params, sort_keys=True, separators=(",", ":"))
        except Exception:
            normalized = str(params)
        return hashlib.sha256(normalized.encode()).hexdigest()[:10]

    def start_run(self, strategy_code: str, version: str, params: Dict[str, Any], universe_source: str, universe_size: int, min_score: int) -> str:
        run_id = str(uuid.uuid4())
        started = self._now_iso()
        params_hash = self.hash_params(params)
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO strategy_run(run_id,strategy_code,version,params_hash,params_json,started_at,universe_source,universe_size,min_score) VALUES(?,?,?,?,?,?,?,?,?)""",
            (run_id, strategy_code, version, params_hash, json.dumps(params, separators=(",", ":")), started, universe_source, universe_size, min_score),
        )
        self.conn.commit()
        return run_id

    def log_result(self, run_id: str, strategy_code: str, ticker: str, passed: bool, score: float, classification: str, reasons, metrics: Dict[str, Any]):
        cur = self.conn.cursor()
        metrics_json = json.dumps(metrics, default=str, separators=(",", ":"))
        cur.execute(
            """INSERT OR REPLACE INTO strategy_result(run_id,strategy_code,ticker,passed,score,classification,reasons,metrics_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                strategy_code,
                ticker,
                1 if passed else 0,
                score,
                classification,
                "" if passed else (";".join(reasons) if isinstance(reasons, (list, tuple)) else str(reasons or "")),
                metrics_json,
                self._now_iso(),
            ),
        )
        # Optional: commit immediately to persist partial progress even if later steps fail
        try:
            self.conn.commit()
        except Exception:
            pass

    def finalize_run(self, run_id: str, exit_status: str = "ok"):
        cur = self.conn.cursor()
        cur.execute("SELECT started_at FROM strategy_run WHERE run_id=?", (run_id,))
        row = cur.fetchone()
        duration_ms = None
        if row:
            try:
                started = row[0]
                # parse naive
                started_dt = datetime.datetime.fromisoformat(started.replace("Z", ""))
                duration_ms = int((datetime.datetime.utcnow() - started_dt).total_seconds() * 1000)
            except Exception:
                pass
        cur.execute(
            "UPDATE strategy_run SET completed_at=?, exit_status=?, duration_ms=? WHERE run_id=?",
            (self._now_iso(), exit_status, duration_ms, run_id),
        )
        self.conn.commit()

__all__ = ["Database"]

def _print_schema_summary(db_path: str):
    """Print schema version, tables, and key columns for verification."""
    db = Database(db_path)
    db.connect()
    conn = db.conn
    cur = conn.cursor()
    try:
        ver = cur.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
        print(f"schema_version: {ver[0] if ver else 'unknown'}")
    except Exception as e:
        print(f"Failed to read schema version: {e}")
    print("\nTables:")
    for (name,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        print(f" - {name}")
    def show(table):
        print(f"\n{table} columns:")
        try:
            for row in cur.execute(f"PRAGMA table_info({table})"):
                _, name, ctype, notnull, dflt, pk = row
                print(f"  {name} {ctype}{' NOT NULL' if notnull else ''}{' PK' if pk else ''}")
        except Exception as e:
            print(f"  (error) {e}")
    for t in ("instruments","holdings","strategy_run","strategy_result"):
        show(t)
    try:
        print("\nRecent results (joined):")
        q = ("SELECT sr.strategy_code,sr.run_id,r.ticker,r.score,r.classification "
             "FROM strategy_run sr JOIN strategy_result r ON sr.run_id=r.run_id "
             "ORDER BY sr.started_at DESC LIMIT 5")
        for row in cur.execute(q):
            print("  ", row)
    except Exception as e:
        print(f"Join sample failed: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SQLite schema inspector for automated-trader")
    parser.add_argument("--db", default="at_data.sqlite", help="Path to sqlite DB (default at_data.sqlite)")
    args = parser.parse_args()
    _print_schema_summary(args.db)
