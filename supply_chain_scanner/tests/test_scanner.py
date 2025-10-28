import pytest
import json
import os
import sys
import subprocess
from unittest.mock import patch, mock_open

# Add the parent directory to the Python path to allow importing the scanner module.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanner import load_data, find_suppliers, trace_supply_chain

@pytest.fixture
def mock_data():
    """Provide mock data for testing."""
    companies_data = [
        {"id": 1, "name": "Client"},
        {"id": 2, "name": "Supplier1"},
        {"id": 3, "name": "Supplier2"}
    ]
    relationships_data = [
        {"supplier_id": 2, "client_id": 1, "asset_class": 1, "product": "P1"},
        {"supplier_id": 3, "client_id": 2, "asset_class": 2, "product": "P2"}
    ]
    return companies_data, relationships_data

def test_find_suppliers(mock_data):
    """Test the find_suppliers function with mock data."""
    companies, relationships = mock_data
    companies_by_id = {c['id']: c for c in companies}

    suppliers = find_suppliers(1, companies_by_id, relationships)
    assert len(suppliers) == 1
    assert suppliers[0]['supplier']['name'] == 'Supplier1'

def test_trace_supply_chain(capsys, mock_data):
    """Test the trace_supply_chain function to ensure correct output."""
    companies, relationships = mock_data
    companies_by_id = {c['id']: c for c in companies}

    # Start tracing from "Client"
    trace_supply_chain(companies[0], companies_by_id, relationships)
    captured = capsys.readouterr()

    expected_output = (
        "  - Supplier1 (Asset Class: 1), Product: P1\n"
        "    - Supplier2 (Asset Class: 2), Product: P2\n"
    )
    assert captured.out == expected_output

def test_main_function_company_found(capsys):
    """Test the main function for a company that exists."""
    # Run the script with "Nvidia Corp" as the company name
    result = subprocess.run(
        ['python3', 'supply_chain_scanner/scanner.py', 'Nvidia Corp'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Nvidia Corp's Full Supply Chain Trace:" in result.stdout
    assert "Micron Technology, Inc." in result.stdout
    assert "ASML Holding NV" in result.stdout

def test_main_function_company_not_found(capsys):
    """Test the main function for a company that does not exist."""
    result = subprocess.run(
        ['python3', 'supply_chain_scanner/scanner.py', 'UnknownCompany'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Company 'UnknownCompany' not found." in result.stdout
