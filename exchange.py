import requests
import json
import logging
from datetime import datetime
from xml.etree import ElementTree
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('exchange_rates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CBR API URL
CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"

def fetch_cbr_rates():
    """
    Fetches exchange rates from Central Bank of Russia.
    Returns a dictionary with currency codes and their rates.
    """
    try:
        response = requests.get(CBR_URL)
        response.encoding = 'utf-8'  # CBR uses windows-1251/utf-8
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch rates: HTTP {response.status_code}")
            return None

        # Parse XML
        root = ElementTree.fromstring(response.text)
        
        # Initialize rates dictionary
        rates = {}
        
        # Process each currency
        for valute in root.findall('Valute'):
            code = valute.find('CharCode').text
            nominal = float(valute.find('Nominal').text.replace(',', '.'))
            value = float(valute.find('Value').text.replace(',', '.'))
            
            # Calculate rate per 1 unit
            rate = value / nominal
            rates[f"{code}_RUB"] = rate

        return rates

    except requests.RequestException as e:
        logger.error(f"Network error: {e}")
        return None
    except ElementTree.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

def save_rates(rates):
    """
    Saves rates to JSON file with current timestamp.
    """
    if rates is None:
        logger.error("No rates to save")
        return False

    data = {
        "timestamp": datetime.now().isoformat(),
        **rates
    }
    
    try:
        with open("exchange_rates.json", "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Exchange rates saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving rates: {e}")
        return False

def load_existing_rates():
    """
    Loads existing rates from JSON file.
    Returns rates dictionary if file exists, None otherwise.
    """
    try:
        if not os.path.exists("exchange_rates.json"):
            return None

        with open("exchange_rates.json", "r") as f:
            data = json.load(f)
            
        # Remove timestamp from rates
        data.pop("timestamp", None)
        return data
    except Exception as e:
        logger.error(f"Error loading existing rates: {e}")
        return None

def update_rates():
    """
    Main function to update exchange rates.
    Always updates timestamp, preserves rates if API fetch fails.
    """
    # Load existing rates
    existing_rates = load_existing_rates()
    
    # Fetch new rates
    logger.info("Fetching new rates from CBR")
    new_rates = fetch_cbr_rates()
    
    if new_rates is None:
        if existing_rates is None:
            logger.error("Failed to fetch new rates and no existing rates available")
            return None
        
        logger.warning("Failed to fetch new rates, keeping existing rates with updated timestamp")
        save_rates(existing_rates)
        return existing_rates
    
    # Save new rates with current timestamp
    save_rates(new_rates)
    return new_rates

def main():
    """
    Runs the exchange rate update process once and exits.
    """
    rates = update_rates()
    if rates:
        logger.info("Current rates:")
        for currency, rate in rates.items():
            logger.info(f"{currency}: {rate:.4f}")
    else:
        logger.error("Failed to update rates")

if __name__ == "__main__":
    main()