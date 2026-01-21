#!/usr/bin/env python3
"""
Setup:
  python3 -m venv venv
  source venv/bin/activate
  python3 -m pip install -r requirements.txt

Run:
  python3 4dmoon.py 2026-01-18
"""

import os
import re
import sys
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector

# =========================
# CONFIG
# =========================
mysql_cfg = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "!@Abc@123",
    "database": "4dmoon",
}

BASE = "https://www.4dmoon.com/past-results/{d}"  # d = YYYY-MM-DD

UA = {
    "User-Agent": "Mozilla/5.0 (compatible; results-scraper/1.0; +https://example.com)"
}

# line yang kita nak “stop” sebab itu footer / navigation
FOOTER_STOPWORDS = {
    "Disclaimer",
    "About Us",
    "Contact Us",
    "Copyright © 2026",
    "4dmoon.com",
    "Powered By 4D King.",
    "|",
}

# =========================
# MYSQL HELPERS
# =========================
def split_title(title: str):
    # contoh title: "Damacai 1+3D" -> provider="Damacai", game="1+3D"
    parts = title.split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return title, ""


def date_exists_in_mysql(d: str, mysql_cfg: dict) -> bool:
    """Return True if at least one row exists for draw_date=d."""
    conn = mysql.connector.connect(**mysql_cfg)
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM draw WHERE draw_date=%s LIMIT 1", (d,))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


def save_to_mysql(d: str, parsed_json: list[dict], mysql_cfg: dict):
    conn = mysql.connector.connect(**mysql_cfg)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # print(f"[3/3] Saving to MySQL... items={len(parsed_json)}")

        for n, x in enumerate(parsed_json, start=1):
            provider, game = split_title(x["title"])
            # print(f"      [{n}/{len(parsed_json)}] upsert: {x['title']}")

            # insert draw (upsert)
            cur.execute(
                """
                INSERT INTO draw (draw_date, provider, game, title, draw_info, first_prize, second_prize, third_prize)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  first_prize=VALUES(first_prize),
                  second_prize=VALUES(second_prize),
                  third_prize=VALUES(third_prize)
                """,
                (
                    d,
                    provider,
                    game,
                    x["title"],
                    x["draw"],
                    x["first"],
                    x["second"],
                    x["third"],
                ),
            )

            # dapatkan draw_id
            cur.execute(
                """
                SELECT id FROM draw
                WHERE draw_date=%s AND title=%s AND draw_info=%s
                LIMIT 1
                """,
                (d, x["title"], x["draw"]),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Cannot find draw row after upsert: {d} {x['title']} {x['draw']}")
            draw_id = row[0]

            # clear prize_number lama (kalau rerun tarikh sama)
            cur.execute("DELETE FROM prize_number WHERE draw_id=%s", (draw_id,))

            # insert special
            for idx, num in enumerate(x["special"], start=1):
                cur.execute(
                    """
                    INSERT INTO prize_number (draw_id, kind, pos, number)
                    VALUES (%s,'special',%s,%s)
                    """,
                    (draw_id, idx, num),
                )

            # insert consolation
            for idx, num in enumerate(x["consolation"], start=1):
                cur.execute(
                    """
                    INSERT INTO prize_number (draw_id, kind, pos, number)
                    VALUES (%s,'consolation',%s,%s)
                    """,
                    (draw_id, idx, num),
                )

            # optional raw lines (uncomment if you want)
            # cur.execute("DELETE FROM raw_line WHERE draw_id=%s", (draw_id,))
            # for ln_no, ln_text in enumerate(x["raw"], start=1):
            #     cur.execute(
            #         "INSERT INTO raw_line(draw_id,line_no,line_text) VALUES (%s,%s,%s)",
            #         (draw_id, ln_no, ln_text[:255]),
            #     )

        conn.commit()
        print("MySQL commit done")
    except Exception:
        conn.rollback()
        print("MySQL rollback (error).")
        raise
    finally:
        cur.close()
        conn.close()


# =========================
# SCRAPER
# =========================
def fetch_lines(d: str) -> list[str]:
    url = BASE.format(d=d)
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]  # remove empty
    return lines


def parse_blocks(lines: list[str]) -> list[dict]:
    blocks = []
    i = 0
    date_line_re = re.compile(r"^\([A-Za-z]{3}\)\s+\d{2}-[A-Za-z]{3}-\d{4}\s+#")

    while i < len(lines) - 1:
        title = lines[i]
        nxt = lines[i + 1]

        if title in {"Past Draw Results", "Date :", "West Malaysia", "East Malaysia", "Singapore"}:
            i += 1
            continue

        if date_line_re.search(nxt):
            block = {"title": title, "draw": nxt, "lines": []}
            j = i + 2
            while j < len(lines):
                # stop bila jumpa footer
                if lines[j] in FOOTER_STOPWORDS:
                    break

                # stop bila masuk block lain
                if j < len(lines) - 1 and date_line_re.search(lines[j + 1]):
                    break

                block["lines"].append(lines[j])
                j += 1

            blocks.append(block)
            i = j
        else:
            i += 1

    return blocks


def extract_numbers(block: dict) -> dict:
    out = {
        "title": block["title"],
        "draw": block["draw"],
        "first": None,
        "second": None,
        "third": None,
        "special": [],
        "consolation": [],
        "raw": block["lines"],
    }

    text = "\n".join(block["lines"])

    # 4D-like
    m = re.search(
        r"1st Prize\s+2nd Prize\s+3rd Prize\s*\n([0-9-]{3,6})\s+([0-9-]{3,6})\s+([0-9-]{3,6})",
        text,
    )
    if m:
        out["first"], out["second"], out["third"] = m.group(1), m.group(2), m.group(3)

    def grab_section(label: str) -> list[str]:
        # capture chunk until next known header or end
        pattern = rf"{label}\s*\n(.*?)(?:\n(?:Consolation|Special|Bonus|Zodiac|Jackpot|WINNING NUMBERS|Lotto|Star Toto|Power Toto|Supreme Toto)\b|$)"
        mm = re.search(pattern, text, flags=re.S)
        if not mm:
            return []
        chunk = mm.group(1)
        # only 4-digit tokens
        return re.findall(r"\b\d{4}\b", chunk)

    out["special"] = grab_section("Special")
    out["consolation"] = grab_section("Consolation")

    # 6-digit variant (e.g., Damacai 3+3D)
    m6 = re.search(r"1st Prize\s+2nd Prize\s+3rd Prize\s*\n(\d{6})\s+(\d{6})\s+(\d{6})", text)
    if m6:
        out["first"], out["second"], out["third"] = m6.group(1), m6.group(2), m6.group(3)

    return out


def scrape_date(d: str):
    print(f"\nFetch page for date: {d}")
    lines = fetch_lines(d)
    # print(f"      fetched lines: {len(lines)}")

    # print(f"[2/3] Parsing blocks...")
    blocks = parse_blocks(lines)
    # print(f"      found blocks: {len(blocks)}")

    parsed = []
    for idx, b in enumerate(blocks, start=1):
        # print(f"      [{idx}/{len(blocks)}] extract: {b.get('title')}")
        parsed.append(extract_numbers(b))

    df = pd.DataFrame(
        [
            {
                "date": d,
                "title": x["title"],
                "draw": x["draw"],
                "first": x["first"],
                "second": x["second"],
                "third": x["third"],
                "special_count": len(x["special"]),
                "consolation_count": len(x["consolation"]),
                "special": ",".join(x["special"]),
                "consolation": ",".join(x["consolation"]),
            }
            for x in parsed
        ]
    )
    return df, parsed


# =========================
# MAIN
# =========================
def main():
    d = "2026-01-17"
    if len(sys.argv) >= 2:
        d = sys.argv[1].strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        print("Usage: python3 4dmoon.py YYYY-MM-DD")
        sys.exit(1)

    # skip kalau tarikh dah ada dlm DB
    if date_exists_in_mysql(d, mysql_cfg):
        print(f"Date {d} already exists in MySQL. Exit.")
        sys.exit(0)

    _, parsed_json = scrape_date(d)

    save_to_mysql(d, parsed_json, mysql_cfg)

    # OUTPUT: JSON sahaja (print + save)
    # print(json.dumps(parsed_json, ensure_ascii=False, indent=2))

    # ensure json/ folder exists
    os.makedirs("json", exist_ok=True)

    json_path = f"json/4dmoon_{d}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(parsed_json, f, ensure_ascii=False, indent=2)

    print(f"Saved JSON to {json_path}")


if __name__ == "__main__":
    main()