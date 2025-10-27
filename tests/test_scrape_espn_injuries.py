"""
Scrape ESPN NBA injuries page for current injury report (free, no API key)
"""
import requests
from bs4 import BeautifulSoup

ESPN_URL = "https://www.espn.com/nba/injuries"

print("\n=== ESPN NBA Injury Report Scraper ===\n")

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    resp = requests.get(ESPN_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # ESPN groups injuries by team in tables
    tables = soup.find_all("table", class_="Table")
    if not tables:
        print("No injury tables found. ESPN may have changed their layout.")
        exit(1)

    total = 0
    for table in tables:
        # Team name is in the previous sibling h2
        team_header = table.find_previous("h2")
        team = team_header.text.strip() if team_header else "Unknown"
        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cols = [td.text.strip() for td in row.find_all("td")]
            if len(cols) < 5:
                continue
            name, pos, date, status, description = cols[:5]
            print(f"{team:15} | {name:20} | {pos:2} | {status:12} | {description}")
            total += 1
    print(f"\nTotal injuries found: {total}")
except Exception as e:
    print(f"Error scraping ESPN: {e}")
