# Automated Trading System

This repository scaffolds an automated trading toolkit and includes a runnable Bullish Breakout Screener.

## Quickstart (Windows PowerShell)

1) (Optional) Create/activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Run the Bullish Breakout Screener

```powershell
# Option A: Scan a predefined universe (default is S&P 500)
python .\bullish_strategy.py --universe sp500 --output .\bullish_breakouts.txt --details .\bullish_breakouts_details.csv --min-volume-multiple 1.5 --strict-macd --require-52w-high

# Option B: Provide a custom list inline
python .\bullish_strategy.py --tickers AAPL MSFT NVDA --details .\bullish_breakouts_details.csv

# Option C: Provide a file with tickers (one per line)
python .\bullish_strategy.py --tickers-file .\portfolio_66.txt --details .\bullish_breakouts_details.csv
```

Flags you can tweak:
- `--min-volume-multiple 1.0|1.5|2.0` Volume spike requirement vs 20d average.
- `--strict-macd` Require MACD > 0 (in addition to crossover + positive histogram).
- `--allow-overbought` Allow RSI > 80.
- `--require-52w-high` Require breakout above prior 52-week high (vs default 6-month high).
- `--tickers AAPL MSFT NVDA` Provide tickers inline instead of a file.
 - `--universe sp500|dow30|nasdaq` Scan a predefined universe when no tickers are provided (default `sp500`).

Outputs:
- `bullish_breakouts.txt` contains only the tickers that passed all criteria.
- `bullish_breakouts_details.csv` contains metrics and reasons for pass/fail per ticker.

## Criteria Implemented

1. Price above SMA10, SMA50, SMA200 (daily).
2. MACD bullish crossover today; histogram > 0; optionally MACD > 0.
3. RSI(14) > 60 and <= 80 (unless `--allow-overbought`).
4. Volume confirmation vs 20-day average (default 1.0x; set higher for stronger signals).
5. Breakout above prior 6-month high (or 52-week high when `--require-52w-high`).

## Files
- `bullish_strategy.py` Screener CLI and logic.
- `sp500_universe.py` Generate an S&P 500 ticker list for inputs to strategies.
- `requirements.txt` Python dependencies.
- `portfolio_66.txt` Sample tickers list (replace with your actual 66 tickers).
- `README.md` This file.

## Notes
- Data fetched via Yahoo Finance (yfinance). Availability and accuracy can vary.
- This is not financial advice. Use at your own risk.

## Generate S&P 500 universe list

```powershell
# Ensure deps are installed
pip install -r requirements.txt

# Generate to sp500_tickers.txt using yfinance (or Wikipedia fallback)
python .\sp500_universe.py --output .\sp500_tickers.txt --source auto

# Use it with the screener
python .\bullish_strategy.py --tickers-file .\sp500_tickers.txt --details .\bullish_breakouts_details.csv --min-volume-multiple 1.5 --strict-macd --require-52w-high
```

## License

Specify your license here.
