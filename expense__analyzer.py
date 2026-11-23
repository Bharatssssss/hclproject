"""
expense_analyzer.py
Personal Expense Analyzer - BCA First Year Individual Project
Author : Bharat Singh  (Admission No. 2026b17910115, BCA-A)
 
Reads a CSV file of expenses, validates and cleans it, then produces:
  * totals by category, month, weekday and payment mode
  * budget alerts (OK / NEAR LIMIT / OVER BUDGET)
  * simple insights and a month-end forecast
  * charts saved as PNG images
 
Usage:
  python expense_analyzer.py report                 full text report
  python expense_analyzer.py charts                 save charts to ./charts
  python expense_analyzer.py add 2026-11-21 Food 250 "Dinner" UPI
"""
import argparse
import calendar
import csv
import os
import sys
from datetime import date, datetime
 
import pandas as pd
import matplotlib
matplotlib.use("Agg")                     # draw charts without opening a window
import matplotlib.pyplot as plt
 
DATA_FILE = "expenses.csv"
COLUMNS = ["date", "category", "description", "payment_mode", "amount"]
 
# Monthly budget limit (in Rs) for each category - edit to suit yourself
BUDGETS = {"Food": 4500, "Transport": 1800, "Shopping": 2500, "Education": 1200,
           "Entertainment": 1200, "Health": 800, "Bills": 1500}
NEAR_LIMIT = 0.80                          # warn when 80% of a budget is used
 
 
# ----------------------------------------------------------- 1. LOAD + CLEAN
def load_expenses(path=DATA_FILE):
    """Read the CSV, drop bad rows and add helper columns."""
    if not os.path.exists(path):
        sys.exit(f"File '{path}' not found. Run generate_sample_data.py first.")
    df = pd.read_csv(path)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"Missing columns in {path}: {missing}")
 
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["category"] = df["category"].astype(str).str.strip().str.title()
    df["payment_mode"] = df["payment_mode"].astype(str).str.strip()
 
    before = len(df)
    df = df.dropna(subset=["date", "amount"])          # unreadable date/amount
    df = df[df["amount"] > 0]                          # amounts must be positive
    dropped = before - len(df)
    if dropped:
        print(f"[note] {dropped} invalid row(s) ignored while loading.")
 
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["weekday"] = df["date"].dt.day_name()
    return df.sort_values("date").reset_index(drop=True)
 
 
# ------------------------------------------------------------- 2. ADD DATA
def add_expense(day, category, amount, description, mode, path=DATA_FILE):
    """Validate one new expense and append it to the CSV file."""
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        sys.exit("Date must be in YYYY-MM-DD format.")
    try:
        amount = float(amount)
    except ValueError:
        sys.exit("Amount must be a number.")
    if amount <= 0:
        sys.exit("Amount must be greater than zero.")
 
    new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        if new_file:
            w.writerow(COLUMNS)
        w.writerow([day, category.strip().title(), description, mode, round(amount, 2)])
    print(f"Added: {day} | {category.title()} | Rs {amount:,.2f} | {description} | {mode}")
 
 
# ------------------------------------------------------------- 3. ANALYSE
def by_category(df):
    t = df.groupby("category")["amount"].agg(["sum", "count", "mean"])
    t.columns = ["total", "transactions", "average"]
    t["share_%"] = (t["total"] / t["total"].sum() * 100).round(1)
    return t.sort_values("total", ascending=False).round(2)
 
 
def by_month(df):
    return df.groupby("month")["amount"].sum().round(2)
 
 
def by_weekday(df):
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return df.groupby("weekday")["amount"].sum().reindex(order).fillna(0).round(2)
 
 
def by_payment_mode(df):
    return df.groupby("payment_mode")["amount"].sum().sort_values(ascending=False).round(2)
 
 
def budget_status(df, month):
    """Compare each category's spend in `month` (e.g. '2026-10') with its budget."""
    spent = df[df["month"] == month].groupby("category")["amount"].sum()
    rows = []
    for cat, limit in BUDGETS.items():
        s = float(spent.get(cat, 0.0))
        used = s / limit
        status = "OVER BUDGET" if used > 1 else "NEAR LIMIT" if used >= NEAR_LIMIT else "OK"
        rows.append([cat, limit, round(s, 2), round(used * 100, 1), status])
    return pd.DataFrame(rows, columns=["category", "budget", "spent", "used_%", "status"])
 
 
def forecast_month_end(df, month):
    """Project a month's total: (spent so far / days passed) x days in month."""
    m = df[df["month"] == month]
    if m.empty:
        return None
    year, mon = map(int, month.split("-"))
    days_in_month = calendar.monthrange(year, mon)[1]
    days_passed = max(m["date"].dt.day.max(), 1)
    spent = m["amount"].sum()
    return round(spent / days_passed * days_in_month, 2), round(spent, 2), days_passed
 
 
def insights(df):
    """Plain-English observations drawn from the data."""
    out = []
    cat = by_category(df)
    out.append(f"Biggest spending category: {cat.index[0]} "
               f"(Rs {cat.iloc[0]['total']:,.0f}, {cat.iloc[0]['share_%']}% of all spending).")
    daily = df.groupby("date")["amount"].sum()
    out.append(f"Highest-spending day: {daily.idxmax():%d %b %Y} (Rs {daily.max():,.0f}).")
    out.append(f"Average spend per day (days with expenses): Rs {daily.mean():,.0f}.")
    wk = by_weekday(df)
    out.append(f"You spend the most on {wk.idxmax()}s (Rs {wk.max():,.0f} in total).")
    months = by_month(df)
    if len(months) >= 2:
        # compare spend PER DAY, so a month that is not finished yet is judged fairly
        def per_day(m):
            sub = df[df["month"] == m]
            y, mo = map(int, m.split("-"))
            days = calendar.monthrange(y, mo)[1]
            if sub["date"].dt.day.max() < days:          # month still running
                days = sub["date"].dt.day.max()
            return sub["amount"].sum() / days
        last, prev = per_day(months.index[-1]), per_day(months.index[-2])
        ch = (last - prev) / prev * 100
        out.append(f"Daily spending in {months.index[-1]} (Rs {last:,.0f}/day) is "
                   f"{'up' if ch >= 0 else 'down'} {abs(ch):.1f}% compared with "
                   f"{months.index[-2]} (Rs {prev:,.0f}/day).")
    top = df.loc[df["amount"].idxmax()]
    out.append(f"Single largest expense: Rs {top['amount']:,.0f} on {top['description']} "
               f"({top['category']}, {top['date']:%d %b %Y}).")
    return out
 
 
# --------------------------------------------------------------- 4. CHARTS
def save_charts(df, folder="charts"):
    os.makedirs(folder, exist_ok=True)
    cat = by_category(df)
 
    plt.figure(figsize=(6, 6))
    plt.pie(cat["total"], labels=cat.index, autopct="%1.1f%%", startangle=90)
    plt.title("Spending share by category")
    plt.savefig(f"{folder}/category_pie.png", dpi=150, bbox_inches="tight"); plt.close()
 
    m = by_month(df)
    plt.figure(figsize=(7, 4))
    plt.bar(m.index, m.values, color="#2E5C8A")
    plt.title("Monthly spending"); plt.ylabel("Rs"); plt.xticks(rotation=30)
    plt.savefig(f"{folder}/monthly_bar.png", dpi=150, bbox_inches="tight"); plt.close()
 
    w = by_weekday(df)
    plt.figure(figsize=(7, 4))
    plt.bar([d[:3] for d in w.index], w.values, color="#1F3A5F")
    plt.title("Spending by day of week"); plt.ylabel("Rs")
    plt.savefig(f"{folder}/weekday_bar.png", dpi=150, bbox_inches="tight"); plt.close()
 
    last = m.index[-1]
    b = budget_status(df, last)
    colors = b["status"].map({"OK": "#3B8E5A", "NEAR LIMIT": "#E0A030", "OVER BUDGET": "#C0392B"})
    plt.figure(figsize=(7, 4))
    plt.bar(b["category"], b["used_%"], color=colors)
    plt.axhline(100, color="black", linestyle="--", linewidth=1)
    plt.title(f"Budget used in {last} (%)"); plt.ylabel("% of budget"); plt.xticks(rotation=30)
    plt.savefig(f"{folder}/budget_bar.png", dpi=150, bbox_inches="tight"); plt.close()
    print(f"4 charts saved in ./{folder}/")
 
 
# --------------------------------------------------------------- 5. REPORT
def print_report(df):
    line = "=" * 62
    print(line); print("PERSONAL EXPENSE ANALYZER - REPORT"); print(line)
    print(f"Period   : {df['date'].min():%d %b %Y} to {df['date'].max():%d %b %Y}")
    print(f"Records  : {len(df)}")
    print(f"Total    : Rs {df['amount'].sum():,.2f}")
 
    print("\n--- Spending by category ---")
    print(by_category(df).to_string())
    print("\n--- Spending by month ---")
    print(by_month(df).to_string())
    print("\n--- Spending by payment mode ---")
    print(by_payment_mode(df).to_string())
 
    months = by_month(df)
    latest = months.index[-1]
    print(f"\n--- Budget check for {latest} ---")
    print(budget_status(df, latest).to_string(index=False))
 
    fc = forecast_month_end(df, latest)
    if fc:
        proj, spent, days = fc
        print(f"\n--- Forecast for {latest} ---")
        print(f"Spent so far (up to day {days}): Rs {spent:,.2f}")
        print(f"Projected month-end total     : Rs {proj:,.2f}")
 
    print("\n--- Insights ---")
    for i in insights(df):
        print(" *", i)
 
 
# ------------------------------------------------------------------- CLI
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Personal Expense Analyzer")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("report", help="print the full analysis report")
    sub.add_parser("charts", help="save charts as PNG files")
    a = sub.add_parser("add", help="add one expense")
    a.add_argument("day"); a.add_argument("category"); a.add_argument("amount")
    a.add_argument("description"); a.add_argument("mode")
    args = ap.parse_args()
 
    if args.cmd == "add":
        add_expense(args.day, args.category, args.amount, args.description, args.mode)
    elif args.cmd == "charts":
        save_charts(load_expenses())
    else:
        print_report(load_expenses())
