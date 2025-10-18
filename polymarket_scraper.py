import json
import requests
import time
import argparse

def fetch_active_event_slugs():
    """Fetches the slugs of all active events."""
    url = "https://gamma-api.polymarket.com/events?closed=false"
    slugs = []
    try:
        response = requests.get(url)
        response.raise_for_status()
        events = response.json()
        for event in events:
            if 'slug' in event:
                slugs.append(event['slug'])
        return slugs
    except requests.exceptions.RequestException as e:
        print(f"Error fetching active event slugs: {e}")
        return None

def fetch_event_details(slug):
    """Fetches the full details for a single event by its slug."""
    url = f"https://gamma-api.polymarket.com/events/slug/{slug}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching event details for slug {slug}: {e}")
        return None

def process_all_active_markets():
    """Fetches all active events, then gets the details for each to process their markets."""
    slugs = fetch_active_event_slugs()
    if not slugs:
        print("No active event slugs found.")
        return []

    all_bets = []
    for slug in slugs:
        print(f"Fetching details for event: {slug}")
        event_details = fetch_event_details(slug)
        if event_details and 'markets' in event_details and event_details['markets']:
            for market in event_details['markets']:
                try:
                    outcomes = json.loads(market.get('outcomes', '[]'))
                    outcome_prices = json.loads(market.get('outcomePrices', '[]'))
                except (json.JSONDecodeError, TypeError):
                    outcomes = []
                    outcome_prices = []

                bet = {
                    'question': market.get('question'),
                    'market_id': market.get('id'),
                    'event_title': event_details.get('title'),
                    'event_slug': event_details.get('slug'),
                    'volume': market.get('volumeNum'),
                    'createdAt': market.get('createdAt'),
                    'closedTime': market.get('closedTime'),
                    'outcomes': outcomes,
                    'outcomePrices': outcome_prices
                }
                all_bets.append(bet)
        time.sleep(0.1) # Be a good citizen and don't spam the API

    # Sort all bets by volume
    all_bets.sort(key=lambda x: x.get('volume') or 0, reverse=True)

    return all_bets


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch and process active Polymarket bets.')
    parser.add_argument('--get-ids', action='store_true', help='If set, the script will only output a list of market IDs.')
    args = parser.parse_args()

    processed_bets = process_all_active_markets()

    if processed_bets:
        if args.get_ids:
            market_ids = [bet['market_id'] for bet in processed_bets]
            with open('bet_ids.json', 'w') as f:
                json.dump(market_ids, f, indent=4)
            print(f"Successfully created bet_ids.json with {len(market_ids)} IDs.")
        else:
            json_output = 'active_bets.json'
            jsonl_output = 'active_bets.jsonl'
            # Write to JSON file
            with open(json_output, 'w') as f:
                json.dump(processed_bets, f, indent=4)

            # Write to JSONL file
            with open(jsonl_output, 'w') as f:
                for bet in processed_bets:
                    f.write(json.dumps(bet) + '\n')

            print(f"Successfully created {json_output} and {jsonl_output} with {len(processed_bets)} bets.")
    else:
        print("Could not process any bets.")