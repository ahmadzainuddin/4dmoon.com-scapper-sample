#!/usr/bin/env python3
# Great thanks to my Indian friend
# who requested this scraper sample ;)

import re
import sys
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE = "https://www.4dmoon.com/past-results/{d}"  # d = YYYY-MM-DD

UA = {
    "User-Agent": "Mozilla/5.0 (compatible; code-master/1.0; +https://www.codemaster.my)"
}

FOOTER_STOPWORDS = {
    "Disclaimer",
    "About Us",
    "Contact Us",
    "Copyright © 2026",
    "4dmoon.com",
    "Powered By 4D King.",
    "|",
}

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
                if lines[j] in FOOTER_STOPWORDS:
                    break

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

    m = re.search(
        r"1st Prize\s+2nd Prize\s+3rd Prize\s*\n([0-9-]{3,6})\s+([0-9-]{3,6})\s+([0-9-]{3,6})",
        text
    )
    if m:
        out["first"], out["second"], out["third"] = m.group(1), m.group(2), m.group(3)

    def grab_section(label: str) -> list[str]:
        pattern = rf"{label}\s*\n(.*?)(?:\n(?:Consolation|Special|Bonus|Zodiac|Jackpot|WINNING NUMBERS|Lotto|Star Toto|Power Toto|Supreme Toto)\b|$)"
        mm = re.search(pattern, text, flags=re.S)
        if not mm:
            return []
        chunk = mm.group(1)
        return re.findall(r"\b\d{4}\b", chunk)

    out["special"] = grab_section("Special")
    out["consolation"] = grab_section("Consolation")

    m6 = re.search(r"1st Prize\s+2nd Prize\s+3rd Prize\s*\n(\d{6})\s+(\d{6})\s+(\d{6})", text)
    if m6:
        out["first"], out["second"], out["third"] = m6.group(1), m6.group(2), m6.group(3)

    return out

def scrape_date(d: str):
    lines = fetch_lines(d)
    blocks = parse_blocks(lines)
    parsed = [extract_numbers(b) for b in blocks]
    df = pd.DataFrame([{
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
    } for x in parsed])
    return df, parsed

def main():
    d = "2026-01-17"
    if len(sys.argv) >= 2:
        d = sys.argv[1].strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        print("Usage: python3 4dmoon.py YYYY-MM-DD")
        sys.exit(1)

    _, parsed_json = scrape_date(d)

    print(json.dumps(parsed_json, ensure_ascii=False, indent=2))

    with open(f"4dmoon_{d}.json", "w", encoding="utf-8") as f:
        json.dump(parsed_json, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
