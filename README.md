# NSE Historical Stock Data Fetcher

A Python command-line utility to fetch historical equity trading data (Open, High, Low, Close, Volume, Turnover, Deliverable Quantity, etc.) directly from the National Stock Exchange of India (NSE) and save it to a CSV file.

It uses `curl-cffi` to mimic standard browser signatures and automatically chunks ranges longer than 365 days to bypass NSE endpoint constraints.

## Features

- Fetches official historical data directly from the NSE API.
- Implements `curl-cffi` to bypass Akamai WAF.
- **Auto-Chunking**: Automatically splits date ranges larger than 365 days into multiple sequential requests and merges them.
- **Period Shorthands**: Supports retrieving data for standard periods (e.g., `1W`, `1M`, `6M`, `1Y`, `3Y`, `5Y`) automatically calculated from the current date.
- Cleans and formats raw data fields (removes commas, normalizes numeric types) for easy analysis in Excel, pandas, or other tools.

## Requirements

- Python 3.6 or higher
- `curl-cffi`
- `pandas`

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/thekrishnasoni/nse_historical_fetcher.git
cd nse_historical_fetcher
pip install -r requirements.txt
```

## Usage

### Fetch by Period Shorthand

Fetch historical data for the last 6 months:
```bash
python fetcher.py --symbol TCS --period 6M
```

Fetch data for the last 1 year and save to a custom file name:
```bash
python fetcher.py --symbol RELIANCE --period 1Y --output reliance_1y.csv
```

### Fetch by Custom Date Range

Fetch historical data between specific dates:
```bash
python fetcher.py --symbol INFY --from-date 01-01-2025 --to-date 05-06-2026
```

## Options

- `-s`, `--symbol`: Stock symbol (e.g., `RELIANCE`, `TCS`, `INFY`).
- `-f`, `--from-date`: Start date in `DD-MM-YYYY` format.
- `-t`, `--to-date`: End date in `DD-MM-YYYY` format.
- `-p`, `--period`: Historical period (e.g., `1W`, `1M`, `3M`, `6M`, `1Y`, `3Y`, `5Y`).
- `-o`, `--output`: Output CSV path (defaults to `{SYMBOL}_historical.csv`).
- `--series`: Stock series (default: `EQ`).

## License

This project is licensed under the MIT License.
