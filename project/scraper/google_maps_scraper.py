# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
from scraper.website_email_extractor import extract_contact_info_batch
import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RequestException),
    reraise=True
)
def scrape_leads(search_query, original_keyword, location_str):
    from bs4 import BeautifulSoup
    import urllib.parse
    import re
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query)}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to fetch DuckDuckGo results: {e}")
        raise
    soup = BeautifulSoup(response.text, 'html.parser')
    
    leads = []
    results = soup.find_all('div', class_='result')
    
    seen_websites = set()
    website_urls = []
    
    for res in results[:10]: # limit to 10 for MVP
        title_el = res.find('a', class_='result__a')
        snippet_el = res.find('a', class_='result__snippet')
        url_el = res.find('a', class_='result__url')
        
        if title_el and url_el:
            company_name = title_el.text
            website_url = url_el.get('href', '')
            if website_url.startswith('//'):
                website_url = 'https:' + website_url
            
            # clean tracking url
            if 'duckduckgo.com/l/?' in website_url:
                import urllib.parse as up
                qs = up.parse_qs(up.urlparse(website_url).query)
                if 'uddg' in qs:
                    website_url = qs['uddg'][0]
                    
            if not website_url or website_url in seen_websites:
                continue
                
            seen_websites.add(website_url)
            website_urls.append(website_url)
            
            lead = {
                "company_name": company_name[:50] + "..." if len(company_name)>50 else company_name,
                "phone": "N/A",  # will be filled in batch from website
                "email": "N/A",  # will be filled in batch
                "address": "N/A",  # will be filled in batch
                "location": location_str, 
                "website": website_url,
                "score": 0
            }
            leads.append(lead)
    
    # Batch extract contact info asynchronously from actual websites
    if website_urls:
        logger.info(f"Extracting contact info from {len(website_urls)} websites...")
        contact_info_list = asyncio.run(extract_contact_info_batch(website_urls))
        for i, lead in enumerate(leads):
            if i < len(contact_info_list):
                lead["phone"] = contact_info_list[i]["phone"]
                lead["email"] = contact_info_list[i]["email"]
                lead["address"] = contact_info_list[i]["address"]
    
    # Scoring
    for lead in leads:
        score = 0
        if lead["website"] != 'N/A': score += 15
        if lead["email"] != 'N/A': score += 25
        if lead["phone"] != 'N/A': score += 25
        if lead["address"] != 'N/A': score += 15
        if original_keyword.lower() in lead["company_name"].lower(): score += 20
        lead["score"] = score
            
    return leads
