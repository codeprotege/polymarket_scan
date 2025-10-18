import json
import requests
import argparse

def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def process_markets(markets, sort_by, json_output_file, jsonl_output_file):
    if not markets:
        print("No market data to process.")
        return

    # The API returns a list directly.
    # Sort by volume or creation date
    if sort_by == 'volume':
        markets.sort(key=lambda x: x.get('volumeNum', 0), reverse=True)
    elif sort_by == 'date':
        markets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)

    bets = []
    for market in markets:
        bet = {
            'question': market.get('question'),
            'volume': market.get('volumeNum'),
            'createdAt': market.get('createdAt'),
            'closedTime': market.get('closedTime'),
            'outcomes': market.get('outcomes'),
            'outcomePrices': market.get('outcomePrices')
        }
        bets.append(bet)

    # Write to JSON file
    with open(json_output_file, 'w') as f:
        json.dump(bets, f, indent=4)

    # Write to JSONL file
    with open(jsonl_output_file, 'w') as f:
        for bet in bets:
            f.write(json.dumps(bet) + '\n')

    print(f"Successfully created {json_output_file} and {jsonl_output_file} sorted by {sort_by}.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch and process Polymarket data.')
    parser.add_argument('--sort_by', type=str, choices=['volume', 'date'], default='volume',
                        help='Sort markets by "volume" or "date".')
    args = parser.parse_args()

    api_url = 'https://gamma-api.polymarket.com/markets'
    market_data = fetch_data(api_url)

    if market_data:
        json_output = f'bets_sorted_by_{args.sort_by}.json'
        jsonl_output = f'bets_sorted_by_{args.sort_by}.jsonl'
        process_markets(market_data, args.sort_by, json_output, jsonl_output)