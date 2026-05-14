import re
import logging
from bs4 import BeautifulSoup
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

# Known aggregator domains
AGGREGATOR_DOMAINS = {
    'justdial.com': 'justdial',
    'sulekha.com': 'sulekha',
    'indiamart.com': 'indiamart',
    'tradeindia.com': 'tradeindia',
    'yellowpages.in': 'yellowpages',
    'cityseeker.com': 'cityseeker',
}

def detect_aggregator(url):
    """Detect if a URL belongs to a known aggregator and return the aggregator type."""
    for domain, agg_type in AGGREGATOR_DOMAINS.items():
        if domain in url.lower():
            return agg_type
    return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RequestException),
    reraise=True
)
def scrape_justdial(url, keyword, location_str):
    """
    Scrape dealer listings from Justdial aggregator pages.
    Justdial pages contain multiple business listings with contact details.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        leads = []
        
        # Justdial uses specific classes for business listings
        # These selectors may need to be updated based on Justdial's current HTML structure
        listings = soup.find_all('div', class_=re.compile(r'listing|store|business', re.I))
        
        for listing in listings[:15]:  # Limit to 15 listings
            try:
                # Extract company name
                name_elem = listing.find(['h2', 'h3', 'span', 'a'], class_=re.compile(r'name|title|store', re.I))
                company_name = name_elem.get_text(strip=True) if name_elem else "N/A"
                
                # Extract phone number
                phone_elem = listing.find(['span', 'a', 'p'], class_=re.compile(r'phone|contact|mobile', re.I))
                phone = phone_elem.get_text(strip=True) if phone_elem else "N/A"
                
                # Extract address
                address_elem = listing.find(['span', 'p', 'div'], class_=re.compile(r'address|location', re.I))
                address = address_elem.get_text(strip=True) if address_elem else "N/A"
                
                # Extract rating if available
                rating_elem = listing.find(['span', 'div'], class_=re.compile(r'rating|star', re.I))
                rating = rating_elem.get_text(strip=True) if rating_elem else "N/A"
                
                # Extract website link if available
                website_elem = listing.find('a', href=re.compile(r'http', re.I))
                website = website_elem.get('href') if website_elem else url
                
                if company_name != "N/A" and company_name != "":
                    lead = {
                        "company_name": company_name[:50] + "..." if len(company_name) > 50 else company_name,
                        "phone": phone,
                        "email": "N/A",  # Justdial doesn't typically show emails
                        "address": address,
                        "location": location_str,
                        "website": website,
                        "score": 0
                    }
                    
                    # Scoring
                    score = 0
                    if website != 'N/A': score += 15
                    if phone != 'N/A': score += 30
                    if address != 'N/A': score += 25
                    if rating != 'N/A': score += 10
                    if keyword.lower() in company_name.lower(): score += 20
                    lead["score"] = score
                    
                    leads.append(lead)
                    
            except Exception as e:
                logger.warning(f"Error parsing Justdial listing: {e}")
                continue
        
        logger.info(f"Extracted {len(leads)} leads from Justdial")
        return leads
        
    except Exception as e:
        logger.error(f"Error scraping Justdial: {e}")
        return []

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RequestException),
    reraise=True
)
def scrape_sulekha(url, keyword, location_str):
    """
    Scrape dealer listings from Sulekha aggregator pages.
    Sulekha pages contain multiple business listings with contact details.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        leads = []
        
        # Sulekha uses specific classes for business listings
        listings = soup.find_all('div', class_=re.compile(r'service|listing|provider|vendor', re.I))
        
        for listing in listings[:15]:  # Limit to 15 listings
            try:
                # Extract company name
                name_elem = listing.find(['h2', 'h3', 'span', 'a'], class_=re.compile(r'name|title|provider', re.I))
                company_name = name_elem.get_text(strip=True) if name_elem else "N/A"
                
                # Extract phone number
                phone_elem = listing.find(['span', 'a', 'p'], class_=re.compile(r'phone|contact|mobile', re.I))
                phone = phone_elem.get_text(strip=True) if phone_elem else "N/A"
                
                # Extract address
                address_elem = listing.find(['span', 'p', 'div'], class_=re.compile(r'address|location', re.I))
                address = address_elem.get_text(strip=True) if address_elem else "N/A"
                
                # Extract rating if available
                rating_elem = listing.find(['span', 'div'], class_=re.compile(r'rating|star|review', re.I))
                rating = rating_elem.get_text(strip=True) if rating_elem else "N/A"
                
                # Extract website link if available
                website_elem = listing.find('a', href=re.compile(r'http', re.I))
                website = website_elem.get('href') if website_elem else url
                
                if company_name != "N/A" and company_name != "":
                    lead = {
                        "company_name": company_name[:50] + "..." if len(company_name) > 50 else company_name,
                        "phone": phone,
                        "email": "N/A",  # Sulekha doesn't typically show emails
                        "address": address,
                        "location": location_str,
                        "website": website,
                        "score": 0
                    }
                    
                    # Scoring
                    score = 0
                    if website != 'N/A': score += 15
                    if phone != 'N/A': score += 30
                    if address != 'N/A': score += 25
                    if rating != 'N/A': score += 10
                    if keyword.lower() in company_name.lower(): score += 20
                    lead["score"] = score
                    
                    leads.append(lead)
                    
            except Exception as e:
                logger.warning(f"Error parsing Sulekha listing: {e}")
                continue
        
        logger.info(f"Extracted {len(leads)} leads from Sulekha")
        return leads
        
    except Exception as e:
        logger.error(f"Error scraping Sulekha: {e}")
        return []

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RequestException),
    reraise=True
)
def scrape_indiamart(url, keyword, location_str):
    """
    Scrape dealer listings from IndiaMART aggregator pages.
    IndiaMART pages contain multiple business listings with contact details.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        leads = []
        
        # IndiaMART uses specific classes for business listings
        listings = soup.find_all('div', class_=re.compile(r'product|supplier|listing', re.I))
        
        for listing in listings[:15]:  # Limit to 15 listings
            try:
                # Extract company name
                name_elem = listing.find(['h2', 'h3', 'span', 'a'], class_=re.compile(r'name|title|company', re.I))
                company_name = name_elem.get_text(strip=True) if name_elem else "N/A"
                
                # Extract phone number
                phone_elem = listing.find(['span', 'a', 'p'], class_=re.compile(r'phone|contact|mobile', re.I))
                phone = phone_elem.get_text(strip=True) if phone_elem else "N/A"
                
                # Extract address
                address_elem = listing.find(['span', 'p', 'div'], class_=re.compile(r'address|location', re.I))
                address = address_elem.get_text(strip=True) if address_elem else "N/A"
                
                # Extract website link if available
                website_elem = listing.find('a', href=re.compile(r'http', re.I))
                website = website_elem.get('href') if website_elem else url
                
                if company_name != "N/A" and company_name != "":
                    lead = {
                        "company_name": company_name[:50] + "..." if len(company_name) > 50 else company_name,
                        "phone": phone,
                        "email": "N/A",
                        "address": address,
                        "location": location_str,
                        "website": website,
                        "score": 0
                    }
                    
                    # Scoring
                    score = 0
                    if website != 'N/A': score += 15
                    if phone != 'N/A': score += 30
                    if address != 'N/A': score += 25
                    if keyword.lower() in company_name.lower(): score += 30
                    lead["score"] = score
                    
                    leads.append(lead)
                    
            except Exception as e:
                logger.warning(f"Error parsing IndiaMART listing: {e}")
                continue
        
        logger.info(f"Extracted {len(leads)} leads from IndiaMART")
        return leads
        
    except Exception as e:
        logger.error(f"Error scraping IndiaMART: {e}")
        return []

def scrape_aggregator(url, keyword, location_str):
    """
    Main function to route to the appropriate aggregator scraper.
    """
    agg_type = detect_aggregator(url)
    
    if not agg_type:
        logger.warning(f"Unknown aggregator type for URL: {url}")
        return []
    
    logger.info(f"Detected aggregator: {agg_type} for URL: {url}")
    
    if agg_type == 'justdial':
        return scrape_justdial(url, keyword, location_str)
    elif agg_type == 'sulekha':
        return scrape_sulekha(url, keyword, location_str)
    elif agg_type == 'indiamart':
        return scrape_indiamart(url, keyword, location_str)
    else:
        logger.warning(f"No scraper implemented for aggregator: {agg_type}")
        return []
