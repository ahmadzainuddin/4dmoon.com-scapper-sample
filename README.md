# 4dmoon Scraper & MySQL Loader

A scraper that collects **4D / Lotto results** from `4dmoon.com`,
stores the data into **MariaDB / MySQL**, and keeps a **JSON archive** for auditing and backup.

Great thanks to my Indian friend who requested this scraper sample ;)
---

## Project Structure

```
4dmoon.com/
├── 4dmoon.py            # Scraper + MySQL insert logic
├── 4dmoon.sql           # Database schema
├── clean_draw_date.py   # Remove dates already existing in DB
├── draw-date.txt        # List of dates to scrape
├── get-draw-date.sh     # Fetch latest available draw dates
├── run.sh               # Automation runner
├── requirements.txt     # Python dependencies
├── json/                # JSON output (auto-generated)
└── venv/                # Python virtual environment
```

---

## Database Setup (One-Time Only)

### MySQL / MariaDB (Local)
```bash
mysql -u root -p < 4dmoon.sql
```

### MySQL with Host & Port
```bash
mysql -h 127.0.0.1 -P 3306 -u root -p < 4dmoon.sql
```

### Verify Database
```sql
USE 4dmoon;
SHOW TABLES;
```

Expected tables:
```
draw
prize_number
raw_line
```

---

## Python Environment Setup

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

### Verify Installation
```bash
python3 -c "import requests, mysql.connector; print('OK')"
```

---

## Make Shell Scripts Executable

```bash
chmod +x *.sh
```

---

## Get Latest Draw Dates

```bash
./get-draw-date.sh
```

Check:
```bash
head draw-date.txt
```

---

## 🧹 Clean Date List (Skip Existing Dates)

```bash
python3 clean_draw_date.py draw-date.txt
```

---

## Run the Scraper

### Single Date
```bash
python3 4dmoon.py 2026-01-18
```

### Automation
```bash
./run.sh
```

Output:
- Data inserted into MySQL
- JSON files stored in `json/`

Example:
```
json/4dmoon_2026-01-18.json
```

---

## Verify Data in MySQL

```sql
SELECT * FROM draw ORDER BY draw_date DESC LIMIT 10;
```

Detailed:
```sql
SELECT
  d.draw_date,
  d.title,
  p.kind,
  p.pos,
  p.number
FROM draw d
JOIN prize_number p ON p.draw_id = d.id
ORDER BY d.draw_date DESC, d.title, p.kind, p.pos;
```

---

## Notes

- Numbers are stored as VARCHAR to preserve leading zeros
- Existing dates are automatically skipped
- MySQL is the primary data source; JSON is for archiving
