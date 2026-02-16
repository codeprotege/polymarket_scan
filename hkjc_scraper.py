import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys
import sqlite3
import os

def init_db(db_path='hkjc_data.db'):
    """Initializes the SQLite database with the required schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            race_date TEXT,
            race_no INTEGER,
            race_info TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER,
            placing TEXT,
            horseno TEXT,
            horse_name TEXT,
            jockey TEXT,
            gear TEXT,
            comment TEXT,
            FOREIGN KEY (race_id) REFERENCES races (id)
        )
    ''')

    conn.commit()
    return conn

def save_to_db(results, db_path='hkjc_data.db'):
    """Saves the scraped results to the SQLite database."""
    conn = init_db(db_path)
    cursor = conn.cursor()

    for race in results:
        url = race['url']
        race_info = race['race_info']

        date_match = re.search(r'date=(\d+)', url, re.IGNORECASE)
        race_no_match = re.search(r'raceno=(\d+)', url, re.IGNORECASE)

        race_date = date_match.group(1) if date_match else "Unknown"
        if race_date == "Unknown":
            date_match = re.search(r'Date=(\d+)', url)
            race_date = date_match.group(1) if date_match else "Unknown"

        race_no = int(race_no_match.group(1)) if race_no_match else 1

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO races (url, race_date, race_no, race_info)
                VALUES (?, ?, ?, ?)
            ''', (url, race_date, race_no, race_info))

            cursor.execute('SELECT id FROM races WHERE url = ?', (url,))
            race_id = cursor.fetchone()[0]

            cursor.execute('DELETE FROM entries WHERE race_id = ?', (race_id,))

            for entry in race['entries']:
                cursor.execute('''
                    INSERT INTO entries (race_id, placing, horseno, horse_name, jockey, gear, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    race_id,
                    entry.get('placing'),
                    entry.get('horseno') or entry.get('horse_no'),
                    entry.get('horse_name') or entry.get('horse'),
                    entry.get('jockey'),
                    entry.get('gear'),
                    entry.get('comment')
                ))
        except sqlite3.Error as e:
            print(f"Database error: {e}")

    conn.commit()
    conn.close()

def get_all_race_dates_in_db(db_path='hkjc_data.db'):
    """Returns all unique race dates from the database."""
    if not os.path.exists(db_path):
        return set()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT race_date FROM races')
    dates = {row[0] for row in cursor.fetchall()}
    conn.close()
    return dates

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://racing.hkjc.com/en-us/local/information/corunning",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def discover_all_dates():
    """Discover all available race dates from the corunning page."""
    url = "https://racing.hkjc.com/en-us/local/information/corunning"
    print(f"Discovering all available dates from {url}...")
    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error discovering dates: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    options = soup.find_all('option')
    dates = []
    for opt in options:
        val = opt.get('value')
        if val and re.match(r'\d{8}', val):
            dates.append(val)

    # Dedup and sort
    dates = sorted(list(set(dates)), reverse=True)
    return dates

def scrape_race(url, headers):
    """Scrapes a single race page."""
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    tables = soup.find_all('table')
    target_table = None
    for table in tables:
        if "Horse" in table.text:
            target_table = table
            break

    if not target_table:
        return None

    race_info = ""
    curr = target_table.find_parent('div')
    if curr:
        potential_infos = curr.find_all('div', recursive=True)
        for div in potential_infos:
            text = div.text.strip()
            if re.search(r'Race \d+', text) and ("HANDICAP" in text.upper() or "CUP" in text.upper() or "PLATE" in text.upper() or "SECTION" in text.upper()):
                race_info = re.sub(r'\s+', ' ', text)
                break

    if not race_info:
        prev = target_table.find_previous_sibling('div')
        while prev:
            text = prev.text.strip()
            if "Race" in text:
                race_info = re.sub(r'\s+', ' ', text)
                break
            prev = prev.find_previous_sibling('div')

    rows = target_table.find_all('tr')
    if not rows:
        return None

    raw_headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
    headers_list = []
    for h in raw_headers:
        h_norm = h.lower()
        h_norm = re.sub(r'[^a-z0-9 ]+', '', h_norm)
        h_norm = h_norm.replace(' ', '_')
        if not h_norm:
            h_norm = f"column_{raw_headers.index(h)}"
        headers_list.append(h_norm)

    entries = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) >= len(headers_list):
            entry = {}
            for i, h in enumerate(headers_list):
                text = cols[i].text.strip()
                text = re.sub(r'\s+', ' ', text)
                entry[h] = text
            entries.append(entry)

    return {
        "url": url,
        "race_info": race_info,
        "entries": entries
    }

def scrape_date(date_str):
    """Scrapes all races for a specific date string (YYYYMMDD)."""
    start_url = f"https://racing.hkjc.com/en-us/local/information/corunning?Date={date_str}"
    headers = get_headers()

    print(f"Scraping date {date_str}...")
    try:
        response = requests.get(start_url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch date page {date_str}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    race_links = soup.find_all('a', href=re.compile(r'raceno=\d+', re.IGNORECASE))

    all_urls_to_scrape = {start_url}
    for link in race_links:
        href = link['href']
        if not href.startswith('http'):
            if href.startswith('/'):
                href = "https://racing.hkjc.com" + href
            else:
                href = "https://racing.hkjc.com/en-us/local/information/" + href

        if "corunning" in href.lower() and date_str in href:
            all_urls_to_scrape.add(href)

    def get_race_no(url):
        match = re.search(r'raceno=(\d+)', url, re.IGNORECASE)
        return int(match.group(1)) if match else 1

    sorted_urls = sorted(list(all_urls_to_scrape), key=get_race_no)

    date_results = []
    for url in sorted_urls:
        print(f"  Scraping {url}...")
        race_data = scrape_race(url, headers)
        if race_data:
            date_results.append(race_data)
        time.sleep(1.0)

    return date_results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='HKJC Scraper')
    parser.add_argument('url', nargs='?', help='URL to scrape a specific meeting (optional)')
    parser.add_argument('--list-dates', action='store_true', help='List all race dates in the database')
    parser.add_argument('--scrape-all', action='store_true', help='Scrape all available dates from the website')
    parser.add_argument('--force', action='store_true', help='Force re-scrape of already processed dates')

    args = parser.parse_args()

    if args.list_dates:
        dates = sorted(list(get_all_race_dates_in_db()), reverse=True)
        if dates:
            print("Found race dates in database:")
            for d in dates:
                print(d)
        else:
            print("No race dates found in database.")
        sys.exit(0)

    if args.scrape_all:
        all_available_dates = discover_all_dates()
        print(f"Found {len(all_available_dates)} available dates.")

        processed_dates = get_all_race_dates_in_db() if not args.force else set()

        dates_to_scrape = [d for d in all_available_dates if d not in processed_dates]
        print(f"{len(dates_to_scrape)} dates to scrape.")

        for i, date_str in enumerate(dates_to_scrape):
            print(f"Processing date {i+1}/{len(dates_to_scrape)}: {date_str}")
            results = scrape_date(date_str)
            if results:
                save_to_db(results)
                print(f"  Saved {len(results)} races for {date_str} to database.")
            else:
                print(f"  No data found for {date_str}.")
            time.sleep(2.0)

        print("Full site scrape complete.")
        sys.exit(0)

    # Default behavior: scrape one date
    if args.url:
        # If it's a date string instead of a URL
        if re.match(r'\d{8}', args.url):
            results = scrape_date(args.url)
        else:
            # Assume it's a start URL
            results = []
            # We need to extract the date to reuse scrape_date or just use the old logic
            date_match = re.search(r'Date=(\d+)', args.url, re.IGNORECASE)
            if date_match:
                results = scrape_date(date_match.group(1))
            else:
                print("Could not extract date from URL. Please provide a standard corunning URL.")
    else:
        # Default date
        results = scrape_date("20260211")

    if results:
        save_to_db(results)
        print("Data exported to SQLite database: hkjc_data.db")
        print(f"Scraping complete. {len(results)} races scraped.")
    else:
        print("No data scraped.")
