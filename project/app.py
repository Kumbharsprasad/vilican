# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, jsonify
import os
import logging
from scraper.google_maps_scraper import scrape_leads
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from groq import Groq
import json

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
os.makedirs('exports', exist_ok=True)

def get_city_from_coords(lat, lon):
    try:
        geolocator = Nominatim(user_agent="ai_lead_gen")
        location = geolocator.reverse(f"{lat}, {lon}", exactly_one=True)
        if location and 'address' in location.raw:
            address = location.raw['address']
            city = address.get('city', address.get('town', address.get('village', address.get('county', 'Unknown'))))
            state = address.get('state', '')
            return f"{city}, {state}".strip(", ")
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
    return "Unknown Location"

def enhance_search_query_with_llm(keyword, location_str):
    prompt = f"""
    The user is looking for businesses related to the keyword: "{keyword}".
    The user is located in or near: "{location_str}".
    
    Understand what the user is actually looking for (e.g. if they type 'TDS Meter', they are looking for 'TDS Meter suppliers, dealers, or manufacturers').
    Return ONLY a highly optimized search query string to be used in a search engine to find businesses, dealers, or suppliers for this product near their location.
    Do not include any explanation or extra text. Just the optimized search query.
    """
    
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.warning("No GROQ_API_KEY found. Using fallback.")
            return f"{keyword} dealers suppliers in {location_str}" # fallback
            
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful search query optimizer for finding local business leads."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
            temperature=0.3,
        )
        return chat_completion.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return f"{keyword} dealers suppliers in {location_str}"

def process_leads_with_llm(leads_data, keyword, location_str):
    prompt = f"""
    Here is a raw list of crawled business leads for a user looking for "{keyword}" near "{location_str}".
    Raw data: {json.dumps(leads_data)}
    
    Your task:
    1. Filter out completely irrelevant results.
    2. Format the names nicely.
    3. Ensure phone numbers, emails, and website URLs are clean. If missing, keep as "N/A".
    4. Calculate or adjust the lead "score" based on completeness (e.g., website=+20, email=+20, phone=+20, relevance=+40). Total 100.
    5. Sort the leads from highest score to lowest score.
    6. Provide the final response EXCLUSIVELY as a valid JSON array of objects with exactly these keys: "company_name", "phone", "email", "location", "website", "score".
    Do not include ANY markdown formatting like ```json ... ```, just the raw JSON text.
    """
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return leads_data
            
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a lead data processing assistant. You always output valid, parseable JSON arrays only."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
            temperature=0.1,
        )
        content = chat_completion.choices[0].message.content.strip()
        # Clean up any potential markdown formatting just in case
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip("` \n")
        
        processed_leads = json.loads(content)
        return processed_leads
    except Exception as e:
        logger.error(f"LLM Processing Error: {e}", exc_info=True)
        return leads_data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-leads', methods=['POST'])
def generate_leads():
    data = request.json
    keyword = data.get('keyword', '').strip()
    user_loc = data.get('location', None)
    
    # Input validation
    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400
    
    if len(keyword) < 2 or len(keyword) > 100:
        return jsonify({"error": "Keyword must be between 2 and 100 characters"}), 400
    
    # Sanitize keyword - remove potentially dangerous characters
    import re
    keyword = re.sub(r'[<>\"\'\;]', '', keyword)
    
    # Validate location if provided
    if user_loc:
        if not isinstance(user_loc, dict):
            return jsonify({"error": "Location must be an object with lat and lon"}), 400
        if 'lat' not in user_loc or 'lon' not in user_loc:
            return jsonify({"error": "Location must include lat and lon coordinates"}), 400
        try:
            lat = float(user_loc['lat'])
            lon = float(user_loc['lon'])
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return jsonify({"error": "Invalid coordinates"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Coordinates must be valid numbers"}), 400
        
    try:
        location_str = "India" # default
        if user_loc and 'lat' in user_loc and 'lon' in user_loc:
            location_str = get_city_from_coords(user_loc['lat'], user_loc['lon'])
            
        optimized_query = enhance_search_query_with_llm(keyword, location_str)
        logger.info(f"Optimized Query: {optimized_query}")
        
        raw_leads = scrape_leads(optimized_query, keyword, location_str)
        logger.info(f"Raw leads crawled: {len(raw_leads)}")
        
        processed_leads = process_leads_with_llm(raw_leads, keyword, location_str)
        logger.info(f"Leads after LLM processing: {len(processed_leads)}")
        
        return jsonify(processed_leads)
    except Exception as e:
        logger.error(f"Error in generate_leads: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
