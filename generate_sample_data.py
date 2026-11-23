"""
generate_sample_data.py
Creates a SYNTHETIC expense file (expenses.csv) for demonstrating the
Personal Expense Analyzer. Replace it with your own real data for real use.
Columns: date, category, description, payment_mode, amount
"""
import random
from datetime import date, timedelta
import pandas as pd
 
random.seed(7)
 
# category -> (descriptions, (min, max) amount in Rs, probability per day)
CATS = {
    "Food":          (["Lunch", "Dinner", "Groceries", "Snacks", "Tea/Coffee"], (40, 450), 0.85),
    "Transport":     (["Metro card", "Auto", "Bus pass", "Cab", "Petrol"], (20, 300), 0.55),
    "Shopping":      (["Clothes", "Shoes", "Accessories", "Online order"], (300, 2500), 0.10),
    "Education":     (["Books", "Stationery", "Online course", "Photocopy"], (50, 1200), 0.10),
    "Entertainment": (["Movie", "Streaming plan", "Games", "Outing"], (100, 700), 0.14),
    "Health":        (["Medicine", "Doctor visit", "Gym"], (80, 900), 0.05),
    "Bills":         (["Mobile recharge", "Internet", "Electricity"], (150, 1200), 0.07),
}
MODES = ["UPI", "Cash", "Card"]
start, end = date(2026, 6, 1), date(2026, 11, 20)
 
rows, d = [], start
while d <= end:
    for cat, (descs, (lo, hi), prob) in CATS.items():
        if random.random() < prob:
            rows.append([d.isoformat(), cat, random.choice(descs),
                         random.choices(MODES, weights=[6, 3, 1])[0],
                         round(random.uniform(lo, hi), 2)])
    d += timedelta(days=1)
 
pd.DataFrame(rows, columns=["date", "category", "description", "payment_mode", "amount"]) \
  .to_csv("expenses.csv", index=False)
print(f"expenses.csv written with {len(rows)} expense records ({start} to {end})")
