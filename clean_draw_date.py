#!/usr/bin/env python3
"""
Remove dates from draw-date.txt that already exist in MySQL (table: draw.draw_date).

Usage:
  python3 clean_draw_date_file.py draw-date.txt

Notes:
- This script will rewrite the input file (safe via temp file + replace).
- It keeps the original order.
"""

import sys
import os
import mysql.connector

mysql_cfg = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "!@Abc@123",
    "database": "4dmoon",
}

def load_dates(path: str) -> list[str]:
    dates = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            d = line.strip()
            if not d:
                continue
            dates.append(d)
    return dates

def fetch_existing_dates(dates: list[str], mysql_cfg: dict) -> set[str]:
    """
    Return set of dates that already exist in draw table.
    Uses IN (...) in chunks to avoid huge query.
    """
    existing = set()
    if not dates:
        return existing

    conn = mysql.connector.connect(**mysql_cfg)
    cur = conn.cursor()
    try:
        chunk_size = 800  # safe chunk for IN list
        for i in range(0, len(dates), chunk_size):
            chunk = dates[i:i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            sql = f"SELECT DISTINCT draw_date FROM draw WHERE draw_date IN ({placeholders})"
            cur.execute(sql, chunk)
            for (draw_date,) in cur.fetchall():
                # mysql-connector returns datetime.date; convert to YYYY-MM-DD
                existing.add(draw_date.isoformat())
    finally:
        cur.close()
        conn.close()

    return existing

def rewrite_file_without_dates(path: str, dates_to_keep: list[str]) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        for d in dates_to_keep:
            f.write(d + "\n")
    os.replace(tmp_path, path)

def main():
    path = "draw-date.txt"
    if len(sys.argv) >= 2:
        path = sys.argv[1].strip()

    dates = load_dates(path)
    if not dates:
        print(f"[INFO] No dates found in {path}. Nothing to do.")
        return

    existing = fetch_existing_dates(dates, mysql_cfg)

    keep = [d for d in dates if d not in existing]
    removed = [d for d in dates if d in existing]

    rewrite_file_without_dates(path, keep)

    print(f"[DONE] File: {path}")
    print(f"       Total in file : {len(dates)}")
    print(f"       Removed (exist in MySQL): {len(removed)}")
    print(f"       Remaining     : {len(keep)}")

    # Optional: print first few removed for confirmation
    if removed:
        print("       Sample removed:", ", ".join(removed[:10]))

if __name__ == "__main__":
    main()
