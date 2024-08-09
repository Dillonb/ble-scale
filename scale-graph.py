#!/usr/bin/env python3
import plotext as plt
import sqlite3
from datetime import datetime
import argparse

parser = argparse.ArgumentParser(
        prog="scale-graph",
        description="Displays data from the scale in a graph"
        )

parser.add_argument('-s', '--sqlite-path', type=str)

args = parser.parse_args()

if not args.sqlite_path:
    parser.print_help()
    exit(1)

def process_date(date):
    dt = datetime.fromisoformat(date)
    return dt.strftime("%Y/%m/%d %H:%M:%S")

conn = sqlite3.connect("/var/lib/syncthing-data/ble-scale-data/sqlite.db")
cur = conn.cursor()
res = cur.execute("select date_iso8601, weight_lb from weights")

dates, prices = zip(*res.fetchall())
dates = [process_date(date) for date in dates]

plt.date_form("Y/m/d H:M:S")
plt.plot(dates, prices)

plt.show()
