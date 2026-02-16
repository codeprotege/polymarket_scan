import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys

def scrape_race(url, headers):
    """Scrapes a single race page."""
    try:
        # Using a session might be better but for simplicity and since it worked:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the data table
    tables = soup.find_all('table')
    target_table = None
    for table in tables:
        # The table of interest has 'Horse Name' in its header
        if "Horse Name" in table.text:
            target_table = table
            break

    if not target_table:
        print(f"Could not find data table on {url}")
        return None

    # Get Race Info from previous siblings
    race_info = ""
    # Search for the div containing race details (Race number, Name, etc.)
    # It usually precedes the table.
    curr = target_table.find_parent('div')
    if curr:
        # Search within the parent div for a div that looks like race info
        potential_infos = curr.find_all('div', recursive=True)
        for div in potential_infos:
            text = div.text.strip()
            if re.search(r'Race \d+', text) and ("HANDICAP" in text.upper() or "CUP" in text.upper() or "PLATE" in text.upper() or "Section" in text):
                race_info = re.sub(r'\s+', ' ', text)
                break

    # Fallback if the above logic fails
    if not race_info:
        prev = target_table.find_previous_sibling('div')
        while prev:
            text = prev.text.strip()
            if "Race" in text:
                race_info = re.sub(r'\s+', ' ', text)
                break
            prev = prev.find_previous_sibling('div')

    # Parse table
    rows = target_table.find_all('tr')
    if not rows:
        return None

    # Extract and clean headers
    raw_headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
    # Normalize headers: lower case, replace spaces with underscores, remove non-alphanumeric
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
                # Clean up internal whitespace
                text = re.sub(r'\s+', ' ', text)
                entry[h] = text
            entries.append(entry)

    return {
        "url": url,
        "race_info": race_info,
        "entries": entries
    }

def scrape_hkjc_corunning(start_url):
    """Scrapes all races for a given date starting from one race URL."""
    # Robust headers to mimic a real browser and potentially bypass simple anti-bot
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://racing.hkjc.com/en-us/local/information/corunning",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    print(f"Fetching start page: {start_url}")
    try:
        response = requests.get(start_url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch start page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all race links for the same day (case-insensitive for raceno)
    race_links = soup.find_all('a', href=re.compile(r'raceno=\d+', re.IGNORECASE))

    all_urls_to_scrape = {start_url}

    for link in race_links:
        href = link['href']
        if not href.startswith('http'):
            if href.startswith('/'):
                href = "https://racing.hkjc.com" + href
            else:
                href = "https://racing.hkjc.com/en-us/local/information/" + href

        # Ensure we only follow corunning links for the same date if possible
        if "corunning" in href.lower():
            all_urls_to_scrape.add(href)

    # Sort URLs by race number
    def get_race_no(url):
        match = re.search(r'raceno=(\d+)', url, re.IGNORECASE)
        return int(match.group(1)) if match else 1

    sorted_urls = sorted(list(all_urls_to_scrape), key=get_race_no)

    all_results = []
    for url in sorted_urls:
        print(f"Scraping {url}...")
        race_data = scrape_race(url, headers)
        if race_data:
            all_results.append(race_data)
        time.sleep(1.5) # Increased delay to be more respectful

    return all_results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        start_url = sys.argv[1]
    else:
        # Default URL from the task
        start_url = "https://racing.hkjc.com/en-us/local/information/corunning?Date=20260211"

    results = scrape_hkjc_corunning(start_url)

    output_file = 'hkjc_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"Scraping complete. {len(results)} races scraped.")
    print(f"Data saved to {output_file}")
