#!/usr/bin/env python3
import plotext as plt
import sqlite3
from datetime import datetime
import argparse

date_format = "%Y/%m/%d %H:%M:%S"

parser = argparse.ArgumentParser(
        prog="scale-graph",
        description="Displays data from the scale in a graph"
        )

parser.add_argument('-s', '--sqlite-path', type=str)
parser.add_argument('-k', '--kilograms', help="Display in kilograms instead of pounds", action='store_true')

args = parser.parse_args()

if not args.sqlite_path:
    parser.print_help()
    exit(1)

conn = sqlite3.connect(args.sqlite_path)
cur = conn.cursor()
unit_column = 'weight_kg' if args.kilograms else 'weight_lb'
res = cur.execute(f"select date_iso8601, {unit_column} from weights")

dates, prices = zip(*res.fetchall())
dates = [datetime.fromisoformat(date).strftime(date_format) for date in dates]

plt.date_form(date_format.replace("%", ""))
plt.plot(dates, prices)

plt.show()
