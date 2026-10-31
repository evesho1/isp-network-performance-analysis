import pandas as pd
import openpyxl
import re
def tdt_to_minutes(val):
    """
    Convert a single TDT cell value into total downtime minutes.
 
    Handles formats seen in the raw export, e.g.:
        "14H 18M", "6h34m", "24H", "17M", "48 M", "0"
    Blank/empty cells are treated as 0 (no recorded downtime).
 
    Returns:
        float minutes, or None if the value couldn't be parsed
        (so it can be flagged for manual review rather than silently
        treated as zero).
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
 
    s = str(val).strip()
    if s == "" or s == "0":
        return 0.0
 
    s_clean = s.upper().replace(" ", "")
    h_match = re.search(r"(\d+(?:\.\d+)?)H", s_clean)
    m_match = re.search(r"(\d+(?:\.\d+)?)M", s_clean)
 
    if not h_match and not m_match:
        return None  # unparseable -> caller should flag this, not assume 0
 
    hours = float(h_match.group(1)) if h_match else 0.0
    minutes = float(m_match.group(1)) if m_match else 0.0
    return hours * 60 + minutes
def find_day_blocks(ws, header_row=3, date_row=2):
    """
    Scan the header row of the sheet to find every day block.
 
    Each day block is identified by a cell in `header_row` containing
    "DOWNTIME". The corresponding date is read from the same column
    in `date_row`. Returns a list of (downtime_column_index, date_value).
    """
    blocks = []
    for col in range(1, ws.max_column + 1):
        header_val = ws.cell(row=header_row, column=col).value
        if header_val and str(header_val).strip().upper() == "DOWNTIME":
            date_val = ws.cell(row=date_row, column=col).value
            blocks.append((col, date_val))
    return blocks
def reshape_month(filepath, sheet_name="Sheet1", bts_col=2,
                   first_data_row=4, header_row=3, date_row=2):
    """
    Reshape one month's wide-format sheet into a tidy long-format DataFrame.
 
    Parameters:
        filepath       : path to the .xlsx file for this month
        sheet_name     : worksheet name (default "Sheet1")
        bts_col        : column index containing BTS/site names (default 2 = col B)
        first_data_row : first row containing BTS data (default 4, after headers)
        header_row     : row containing "DOWNTIME"/"UPTIME"/"TDT" labels (default 3)
        date_row       : row containing the date for each day block (default 2)
 
    Returns:
        tidy_df   : DataFrame with columns [bts, date, downtime_minutes]
        unparsed  : list of (bts, date, raw_value) for any TDT cells that
                    couldn't be parsed — review these manually before
                    trusting the aggregated totals.
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb[sheet_name]
 
    day_blocks = find_day_blocks(ws, header_row=header_row, date_row=date_row)
    if not day_blocks:
        raise ValueError(
            "No day blocks found — check that header_row/date_row match "
            "this sheet's layout."
        )
 
    rows = []
    unparsed = []
 
    for r in range(first_data_row, ws.max_row + 1):
        bts = ws.cell(row=r, column=bts_col).value
        if not bts or not str(bts).strip():
            continue  # skip blank rows
        bts_clean = str(bts).strip()
 
        for downtime_col, date_val in day_blocks:
            tdt_col = downtime_col + 2  # TDT sits 2 columns after DOWNTIME
            raw_val = ws.cell(row=r, column=tdt_col).value
            minutes = tdt_to_minutes(raw_val)
 
            if minutes is None:
                unparsed.append((bts_clean, date_val, raw_val))
                minutes = 0.0  # default so the pipeline doesn't break;
                                # the row is still flagged in `unparsed`
 
            rows.append({
                "bts": bts_clean,
                "date": date_val,
                "downtime_minutes": minutes
            })
 
    tidy_df = pd.DataFrame(rows)
    return tidy_df, unparsed
def calculate_monthly_uptime(tidy_df):
    """
    Aggregate daily downtime into monthly uptime % per BTS.
 
    Uses the number of distinct days actually present in the data as the
    denominator (rather than assuming a fixed 30/31-day month), so any
    gaps in monitoring don't silently get treated as "fully up".
    """
    days_in_data = tidy_df["date"].nunique()
    total_minutes_available = days_in_data * 1440  # 1440 minutes/day
 
    monthly = (
        tidy_df.groupby("bts")["downtime_minutes"]
        .sum()
        .reset_index()
        .rename(columns={"downtime_minutes": "total_downtime_minutes"})
    )
    monthly["uptime_percent"] = (
        1 - monthly["total_downtime_minutes"] / total_minutes_available
    ) * 100
 
    return monthly, days_in_data
 
 
if __name__ == "__main__":
    # --- Example usage for a single month ---
    FILEPATH = "/Users/rotoms/Documents/Connekt presentation Data/Test for CDBMS copy.xlsx"  # replace with your file path
 
    tidy_df, unparsed = reshape_month(FILEPATH)
 
    print(f"Reshaped {len(tidy_df)} rows.")
    print(f"Unparsed TDT values: {len(unparsed)}")
    for u in unparsed[:10]:
        print("  Needs review:", u)
 
    # Save tidy long-format table (this is what would feed into SQL)
    tidy_df.to_csv("bts_daily_tidy.csv", index=False)
 
    # Calculate monthly uptime % per BTS, and overall network average
    monthly_summary, days_used = calculate_monthly_uptime(tidy_df)
    print(f"\nCalculated using {days_used} days present in the data.")
    print(f"Network-wide average uptime %: {monthly_summary['uptime_percent'].mean():.3f}")
 
    monthly_summary.to_csv("bts_monthly_uptime_summary.csv", index=False)
    print("\nSaved: bts_daily_tidy.csv, bts_monthly_uptime_summary.csv")
