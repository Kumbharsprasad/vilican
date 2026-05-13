import aiohttp
import asyncio
import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    reraise=True
)
async def extract_email_from_website(url, session):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch {url}: status {response.status}")
                return "N/A"
                
            text = await response.text()
            # Regex for email
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, text)
            
            # Filter out common false positives
            valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
            
            if valid_emails:
                return valid_emails[0]
                
            # Try contact page
            soup = BeautifulSoup(text, 'html.parser')
            contact_link = soup.find('a', href=re.compile(r'contact', re.I))
            if contact_link:
                contact_url = urljoin(url, contact_link.get('href'))
                async with session.get(contact_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as c_response:
                    if c_response.status == 200:
                        c_text = await c_response.text()
                        c_emails = re.findall(email_pattern, c_text)
                        c_valid_emails = [e for e in c_emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
                        if c_valid_emails:
                            return c_valid_emails[0]
                
    except Exception as e:
        logger.error(f"Error extracting email from {url}: {e}")
        pass
        
    return "N/A"

async def extract_emails_batch(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [extract_email_from_website(url, session) for url in urls]
        return await asyncio.gather(*tasks)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    reraise=True
)
async def extract_contact_info_from_website(url, session):
    """
    Extract comprehensive contact information from a website:
    - Phone numbers
    - Email addresses
    - Physical address
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch {url}: status {response.status}")
                return {"phone": "N/A", "email": "N/A", "address": "N/A"}
                
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            
            # Extract phone numbers (multiple patterns for Indian and international formats)
            phone_patterns = [
                r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # International
                r'\d{10}',  # Simple 10-digit
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            ]
            
            phones = []
            for pattern in phone_patterns:
                phones.extend(re.findall(pattern, text))
            
            # Clean and deduplicate phones
            cleaned_phones = []
            seen_phones = set()
            for phone in phones:
                # Clean the phone number
                phone_clean = re.sub(r'[^\d+]', '', phone)
                if len(phone_clean) >= 10 and phone_clean not in seen_phones:
                    seen_phones.add(phone_clean)
                    cleaned_phones.append(phone)
            
            phone = cleaned_phones[0] if cleaned_phones else "N/A"
            
            # Extract email
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, text)
            valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
            email = valid_emails[0] if valid_emails else "N/A"
            
            # Extract address - look for common address patterns
            address = "N/A"
            
            # Try to find address in common sections
            address_keywords = ['address', 'location', 'contact us', 'find us', 'visit us']
            for keyword in address_keywords:
                # Search in text
                addr_pattern = rf'{keyword}[:\s]*([^\n\.]{20,150})'
                matches = re.findall(addr_pattern, text, re.IGNORECASE)
                if matches:
                    address = matches[0].strip()
                    break
            
            # Try to find address in HTML elements
            if address == "N/A":
                for tag in soup.find_all(['p', 'div', 'span'], class_=re.compile(r'address|location', re.I)):
                    if tag.get_text(strip=True) and len(tag.get_text(strip=True)) > 20:
                        address = tag.get_text(strip=True)
                        break
            
            # If still no address, try contact page
            if address == "N/A" or email == "N/A":
                contact_link = soup.find('a', href=re.compile(r'contact', re.I))
                if contact_link:
                    contact_url = urljoin(url, contact_link.get('href'))
                    try:
                        async with session.get(contact_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as c_response:
                            if c_response.status == 200:
                                c_text = await c_response.text()
                                c_soup = BeautifulSoup(c_text, 'html.parser')
                                
                                # Extract email from contact page
                                if email == "N/A":
                                    c_emails = re.findall(email_pattern, c_text)
                                    c_valid_emails = [e for e in c_emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
                                    if c_valid_emails:
                                        email = c_valid_emails[0]
                                
                                # Extract phone from contact page
                                if phone == "N/A":
                                    for pattern in phone_patterns:
                                        c_phones = re.findall(pattern, c_text)
                                        if c_phones:
                                            phone = c_phones[0]
                                            break
                                
                                # Extract address from contact page
                                if address == "N/A":
                                    for keyword in address_keywords:
                                        addr_pattern = rf'{keyword}[:\s]*([^\n\.]{20,150})'
                                        matches = re.findall(addr_pattern, c_text, re.IGNORECASE)
                                        if matches:
                                            address = matches[0].strip()
                                            break
                    except Exception as e:
                        logger.warning(f"Failed to fetch contact page for {url}: {e}")
            
            return {
                "phone": phone,
                "email": email,
                "address": address
            }
                
    except Exception as e:
        logger.error(f"Error extracting contact info from {url}: {e}")
        return {"phone": "N/A", "email": "N/A", "address": "N/A"}

async def extract_contact_info_batch(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [extract_contact_info_from_website(url, session) for url in urls]
        return await asyncio.gather(*tasks)
