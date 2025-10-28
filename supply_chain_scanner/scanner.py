import json
import argparse
import os

def load_data():
    """Loads and preprocesses data from JSON files."""
    script_dir = os.path.dirname(__file__)

    with open(os.path.join(script_dir, 'database/companies.json'), 'r') as f:
        companies_list = json.load(f)

    with open(os.path.join(script_dir, 'database/relationships.json'), 'r') as f:
        relationships = json.load(f)

    companies_by_id = {company['id']: company for company in companies_list}
    companies_by_name = {company['name'].lower(): company for company in companies_list}

    return companies_by_id, companies_by_name, relationships

def find_suppliers(company_id, companies_by_id, relationships):
    """Finds suppliers for a given company using efficient lookups."""
    suppliers = []
    for rel in relationships:
        if rel['client_id'] == company_id:
            supplier = companies_by_id.get(rel['supplier_id'])
            if supplier:
                suppliers.append({
                    'supplier': supplier,
                    'asset_class': rel['asset_class'],
                    'product': rel['product']
                })
    return suppliers

def trace_supply_chain(company, companies_by_id, relationships, level=0):
    """Recursively traces the supply chain for a given company."""
    suppliers = find_suppliers(company['id'], companies_by_id, relationships)
    for supplier_info in suppliers:
        indent = "  " * (level + 1)
        print(f"{indent}- {supplier_info['supplier']['name']} (Asset Class: {supplier_info['asset_class']}), Product: {supplier_info['product']}")
        trace_supply_chain(supplier_info['supplier'], companies_by_id, relationships, level + 1)

def main():
    """Main function to run the scanner from the command line."""
    parser = argparse.ArgumentParser(description="Trace the supply chain of a specified company.")
    parser.add_argument("company_name", help="The name of the company to trace.")
    args = parser.parse_args()

    companies_by_id, companies_by_name, relationships = load_data()

    target_company = companies_by_name.get(args.company_name.lower())

    if target_company:
        print(f"{target_company['name']}'s Full Supply Chain Trace:")
        trace_supply_chain(target_company, companies_by_id, relationships)
    else:
        print(f"Company '{args.company_name}' not found.")

if __name__ == '__main__':
    main()
