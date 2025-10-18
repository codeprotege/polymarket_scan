import requests
import xml.etree.ElementTree as ET
import json
import time
from urllib.parse import urlparse
import os

def get_sitemap_urls(sitemap_index_url):
    """Fetches and parses the main sitemap to get URLs of other sitemaps."""
    print(f"Fetching main sitemap: {sitemap_index_url}")
    try:
        response = requests.get(sitemap_index_url)
        response.raise_for_status()
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        root = ET.fromstring(response.content)
        sitemap_urls = []
        for url_element in root.findall('ns:url', namespaces):
            loc = url_element.find('ns:loc', namespaces)
            if loc is not None and 'sitemap-events' in loc.text:
                sitemap_urls.append(loc.text)
        return sitemap_urls
    except (requests.exceptions.RequestException, ET.ParseError) as e:
        print(f"Error fetching or parsing main sitemap: {e}")
        return []

def get_event_urls_from_sitemap(sitemap_url):
    """Fetches and parses an individual sitemap to get event URLs."""
    print(f"Fetching event sitemap: {sitemap_url}")
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        root = ET.fromstring(response.content)
        event_urls = []
        for url_element in root.findall('ns:url', namespaces):
            loc = url_element.find('ns:loc', namespaces)
            if loc is not None and '/event/' in loc.text:
                event_urls.append(loc.text)
        return event_urls
    except (requests.exceptions.RequestException, ET.ParseError) as e:
        print(f"Error fetching or parsing event sitemap {sitemap_url}: {e}")
        return []

def extract_slug_from_url(url):
    """Extracts the event slug from a URL."""
    path = urlparse(url).path
    parts = path.split('/')
    if len(parts) >= 3 and parts[1] == 'event':
        return parts[2]
    return None

def fetch_event_details(slug):
    """Fetches the full details for a single event by its slug."""
    url = f"https://gamma-api.polymarket.com/events/slug/{slug}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching event details for slug {slug}: {e}")
        return None

def deep_scan_for_market_ids():
    """Performs a deep, resumable scan of Polymarket to find all market IDs."""
    slugs_file = 'all_slugs.json'
    bet_ids_file = 'all_bet_ids.json'
    processed_slugs_file = 'processed_slugs.json'

    # Step 1: Get all slugs from sitemaps if not already done
    if os.path.exists(slugs_file):
        print("Loading slugs from existing file...")
        with open(slugs_file, 'r') as f:
            all_slugs = set(json.load(f))
    else:
        print("Fetching all slugs from sitemaps...")
        main_sitemap_url = "https://polymarket.com/sitemap.xml"
        sitemap_urls = get_sitemap_urls(main_sitemap_url)
        all_event_urls = []
        for sitemap_url in sitemap_urls:
            all_event_urls.extend(get_event_urls_from_sitemap(sitemap_url))
            time.sleep(0.1)
        all_slugs = {extract_slug_from_url(url) for url in all_event_urls if extract_slug_from_url(url)}
        with open(slugs_file, 'w') as f:
            json.dump(list(all_slugs), f)
        print(f"Saved {len(all_slugs)} unique slugs to {slugs_file}.")

    # Step 2: Load progress
    processed_slugs = set()
    if os.path.exists(processed_slugs_file):
        with open(processed_slugs_file, 'r') as f:
            processed_slugs = set(json.load(f))

    all_market_ids = set()
    if os.path.exists(bet_ids_file):
        with open(bet_ids_file, 'r') as f:
            all_market_ids = set(json.load(f))

    print(f"Found {len(all_slugs)} total slugs. {len(processed_slugs)} already processed.")

    # Step 3: Process remaining slugs
    slugs_to_process = all_slugs - processed_slugs

    for i, slug in enumerate(slugs_to_process):
        print(f"Processing slug {i+1}/{len(slugs_to_process)}: {slug}")
        event_details = fetch_event_details(slug)
        if event_details and 'markets' in event_details and event_details['markets']:
            for market in event_details['markets']:
                if 'id' in market:
                    all_market_ids.add(market['id'])

        # Save progress after each slug
        processed_slugs.add(slug)
        with open(processed_slugs_file, 'w') as f:
            json.dump(list(processed_slugs), f)
        with open(bet_ids_file, 'w') as f:
            json.dump(list(all_market_ids), f, indent=4)

        time.sleep(0.1)

    return list(all_market_ids)


if __name__ == "__main__":
    print("Starting deep scan...")
    market_ids = deep_scan_for_market_ids()

    print(f"\nScan complete. Found {len(market_ids)} total bet IDs.")
    print(f"Results are saved in all_bet_ids.json")