import requests
import json
import logging
from datetime import datetime
from xml.etree import ElementTree
import time
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
    Saves rates to JSON file with timestamp.
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
    Returns None if file doesn't exist or is too old.
    """
    try:
        if not os.path.exists("exchange_rates.json"):
            return None

        with open("exchange_rates.json", "r") as f:
            data = json.load(f)
            
        # Check if rates are from today
        timestamp = datetime.fromisoformat(data.pop("timestamp"))
        if timestamp.date() != datetime.now().date():
            return None
            
        return data
    except Exception as e:
        logger.error(f"Error loading existing rates: {e}")
        return None

def update_rates():
    """
    Main function to update exchange rates.
    Only fetches new rates if necessary.
    """
    # Try to load existing rates first
    existing_rates = load_existing_rates()
    if existing_rates is not None:
        logger.info("Using existing rates from today")
        return existing_rates

    # Fetch new rates if needed
    logger.info("Fetching new rates from CBR")
    rates = fetch_cbr_rates()
    if rates is not None:
        save_rates(rates)
        return rates
    
    return None

def main():
    """
    Main execution function.
    Can be run as a script or imported and called.
    """
    while True:
        try:
            rates = update_rates()
            if rates:
                logger.info("Current rates:")
                for currency, rate in rates.items():
                    logger.info(f"{currency}: {rate:.4f}")
            else:
                logger.error("Failed to update rates")

            # Wait for 24 hours before next update
            # In production, you might want to use a proper scheduler
            time.sleep(24 * 60 * 60)  # 24 hours

        except KeyboardInterrupt:
            logger.info("Exchange rate updater stopped")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == "__main__":
    main()
