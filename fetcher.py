#!/usr/bin/env python3
"""
NSE Historical Stock Data Fetcher

This utility fetches historical equity trading data (Open, High, Low, Close,
Volume, Turnover, Deliverable Quantity, etc.) directly from the National
Stock Exchange of India (NSE) and exports it to a CSV file.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from io import StringIO
from typing import Optional, List
import pandas as pd
from curl_cffi import requests

BASE_URL = "https://www.nseindia.com"
HISTORICAL_URL = "https://www.nseindia.com/api/historicalOR/generateSecurityWiseHistoricalData"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest"
}


def get_nse_session() -> requests.Session:
    """
    Initializes a session and loads the NSE homepage to establish cookies.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        # Step 1: visit landing page
        response = session.get(BASE_URL, impersonate="chrome", timeout=10)
        response.raise_for_status()
        time.sleep(1.5)
        # Step 2: visit report detail page to configure session context
        session.get(f"{BASE_URL}/report-detail/eq_historical", impersonate="chrome", timeout=10)
        time.sleep(1.0)
    except Exception as e:
        print(f"Error initializing session with NSE website: {e}", file=sys.stderr)
        raise
    return session


def fetch_historical_chunk(session: requests.Session, symbol: str, from_date: str, to_date: str, series: str = "EQ") -> Optional[pd.DataFrame]:
    """
    Fetches a single chunk of historical data (maximum 365 days) from NSE.
    Dates must be in DD-MM-YYYY format.
    """
    clean_symbol = symbol.upper().replace("&", "%26")
    params = {
        "from": from_date,
        "to": to_date,
        "symbol": clean_symbol,
        "type": "priceVolumeDeliverable",
        "series": series,
        "csv": "true"
    }

    try:
        response = session.get(HISTORICAL_URL, params=params, impersonate="chrome", timeout=15)
        if response.status_code in [401, 403]:
            # Session might have expired, re-initialize
            session = get_nse_session()
            response = session.get(HISTORICAL_URL, params=params, impersonate="chrome", timeout=15)

        if response.status_code != 200:
            print(f"Failed to fetch data for {symbol} ({from_date} to {to_date}). HTTP Status: {response.status_code}", file=sys.stderr)
            return None

        csv_data = response.text.replace("\x82", "").replace("â¹", "In Rs")
        if "No Records" in csv_data or len(csv_data.strip().split("\n")) <= 1:
            return pd.DataFrame()

        df = pd.read_csv(StringIO(csv_data))
        # Strip whitespaces from column names
        df.columns = [col.strip() for col in df.columns]
        return df

    except Exception as e:
        print(f"Error fetching data for chunk {from_date} to {to_date}: {e}", file=sys.stderr)
        return None


def split_date_range(from_dt: datetime, to_dt: datetime) -> List[tuple]:
    """
    Splits a date range into chunks of maximum 365 days.
    """
    chunks = []
    current_from = from_dt

    while current_from <= to_dt:
        current_to = min(current_from + timedelta(days=364), to_dt)
        chunks.append((current_from.strftime("%d-%m-%Y"), current_to.strftime("%d-%m-%Y")))
        current_from = current_to + timedelta(days=1)

    return chunks


def parse_period(period_str: str) -> tuple:
    """
    Converts period shorthand (e.g. 1M, 6M, 1Y) to (from_date, to_date) datetime objects.
    """
    to_dt = datetime.now()
    period_str = period_str.upper()
    
    if period_str.endswith("D"):
        days = int(period_str[:-1])
        from_dt = to_dt - timedelta(days=days)
    elif period_str.endswith("W"):
        weeks = int(period_str[:-1])
        from_dt = to_dt - timedelta(weeks=weeks)
    elif period_str.endswith("M"):
        months = int(period_str[:-1])
        from_dt = to_dt - timedelta(days=months * 30)
    elif period_str.endswith("Y"):
        years = int(period_str[:-1])
        from_dt = to_dt - timedelta(days=years * 365)
    else:
        raise ValueError(f"Invalid period format: '{period_str}'. Use format like 1M, 6M, 1Y.")
        
    return from_dt, to_dt


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans up string formatting and numeric columns in the dataframe.
    """
    # Sort by date ascending
    if "Date" in df.columns:
        df["Parsed_Date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
        df = df.dropna(subset=["Parsed_Date"]).sort_values("Parsed_Date")
        df = df.drop(columns=["Parsed_Date"])

    # Clean numeric columns with commas
    cols_to_clean = ["Prev Close", "Open Price", "High Price", "Low Price", "Last Price",
                     "Close Price", "Average Price", "Total Traded Quantity", "Turnover ₹",
                     "No. of Trades", "Deliverable Qty", "% Dly Qt to Traded Qty"]

    for col in cols_to_clean:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def main():
    parser = argparse.ArgumentParser(description="Fetch historical stock data from NSE.")
    parser.add_argument("-s", "--symbol", required=True, help="Stock symbol (e.g., RELIANCE, TCS)")
    parser.add_argument("-f", "--from-date", help="Start date in DD-MM-YYYY format")
    parser.add_argument("-t", "--to-date", help="End date in DD-MM-YYYY format")
    parser.add_argument("-p", "--period", help="Historical period (e.g. 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y)")
    parser.add_argument("-o", "--output", help="Output CSV path (defaults to {symbol}_historical.csv)")
    parser.add_argument("--series", default="EQ", help="Stock series (default: EQ)")

    args = parser.parse_args()

    # Determine dates
    if args.period:
        try:
            from_dt, to_dt = parse_period(args.period)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.from_date and args.to_date:
        try:
            from_dt = datetime.strptime(args.from_date, "%d-%m-%Y")
            to_dt = datetime.strptime(args.to_date, "%d-%m-%Y")
        except ValueError:
            print("Error: Dates must be in DD-MM-YYYY format.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Either --period or both --from-date and --to-date must be specified.", file=sys.stderr)
        sys.exit(1)

    if from_dt > to_dt:
        print("Error: Start date cannot be after end date.", file=sys.stderr)
        sys.exit(1)

    output_path = args.output if args.output else f"{args.symbol.upper()}_historical.csv"

    print(f"Initializing connection to NSE for {args.symbol.upper()}...")
    try:
        session = get_nse_session()
    except Exception:
        sys.exit(1)

    # Split range into chunks of max 365 days
    chunks = split_date_range(from_dt, to_dt)
    all_dfs = []

    print(f"Fetching data from {from_dt.strftime('%d-%m-%Y')} to {to_dt.strftime('%d-%m-%Y')} ({len(chunks)} chunk(s))...")

    for i, (chunk_from, chunk_to) in enumerate(chunks):
        if len(chunks) > 1:
            print(f"Retrieving chunk {i+1}/{len(chunks)}: {chunk_from} to {chunk_to}...")
        
        df = fetch_historical_chunk(session, args.symbol, chunk_from, chunk_to, args.series)
        if df is not None and not df.empty:
            all_dfs.append(df)
        
        # Polite delay to prevent rate limits
        if len(chunks) > 1 and i < len(chunks) - 1:
            time.sleep(1.5)

    if not all_dfs:
        print("No historical records found for the requested symbol/date range.")
        sys.exit(1)

    # Merge and clean data
    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df = clean_dataframe(final_df)

    try:
        final_df.to_csv(output_path, index=False)
        print(f"Successfully saved {len(final_df)} rows to: {output_path}")
    except OSError as e:
        print(f"Error saving file to {output_path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
