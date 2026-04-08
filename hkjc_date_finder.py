import requests
from bs4 import BeautifulSoup
import time
import re
import sys
from datetime import datetime

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://racing.hkjc.com/en-us/local/information/fixture",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def fetch_with_retry(url, headers, timeout=30, retries=3):
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            if i == retries - 1:
                raise e
            print(f"  Retry {i+1}/{retries} for {url} due to: {e}", file=sys.stderr)
            time.sleep(2 * (i + 1))

def discover_dates_in_range(start_year=2015, end_year=None):
    """Discovers all HKJC race dates from start_year to present by checking fixture pages."""
    if end_year is None:
        end_year = datetime.now().year

    all_dates = []
    headers = get_headers()

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if year == datetime.now().year and month > datetime.now().month + 1:
                break

            url = f"https://racing.hkjc.com/en-us/local/information/fixture?calyear={year}&calmonth={month:02d}"
            print(f"Checking fixtures for {year}/{month:02d}...", file=sys.stderr)
            try:
                response = fetch_with_retry(url, headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                tds = soup.find_all('td')
                for td in tds:
                    # Check for meeting indicator (img)
                    if td.find('img', src=re.compile(r'/(st|hv|ch)\.gif')):
                        # Extract the day number from the text
                        day_match = re.search(r'(\d+)', td.get_text())
                        if day_match:
                            day = int(day_match.group(1))
                            if 1 <= day <= 31:
                                date_str = f"{year}{month:02d}{day:02d}"
                                all_dates.append(date_str)
                time.sleep(0.5) # Polite delay
            except Exception as e:
                print(f"Error fetching fixture for {year}/{month:02d}: {e}", file=sys.stderr)

    return sorted(list(set(all_dates)), reverse=True)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='HKJC Race Date Finder')
    parser.add_argument('--start-year', type=int, default=2015, help='Start year for date discovery (default: 2015)')
    parser.add_argument('--end-year', type=int, help='End year for date discovery')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    dates = discover_dates_in_range(args.start_year, args.end_year)

    if args.json:
        print(json.dumps(dates))
    else:
        for d in dates:
            print(d)

    print(f"Total dates found: {len(dates)}", file=sys.stderr)
