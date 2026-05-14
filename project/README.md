# 🤖 AI Lead Generator

An intelligent, automated business lead generation tool that combines **web scraping**, **AI-powered query optimization**, and **LLM-based data processing** to discover and rank business leads based on a product keyword and user location.

---

## 📌 Project Overview

This tool helps users find B2B business leads (dealers, suppliers, distributors) for any product by:
1. Taking a product keyword and user's GPS location as input
2. Using an LLM (Groq + LLaMA) to generate an optimized search query
3. Scraping search results from DuckDuckGo + business aggregator websites
4. Extracting contact info (phone, email, address) from individual business websites
5. Scoring and ranking leads by data completeness and relevance
6. Displaying results in a clean web dashboard with CSV export

---

## 🗂️ Project Structure

```
project/
├── app.py                          # Flask backend - main API server
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (GROQ_API_KEY)
├── .gitignore
├── app.log                         # Application logs
├── exports/                        # CSV exports saved here
├── templates/
│   └── index.html                  # Frontend dashboard (HTML)
├── static/
│   ├── style.css                   # UI styling
│   └── script.js                   # Frontend JavaScript logic
└── scraper/
    ├── google_maps_scraper.py       # Core DuckDuckGo search scraper
    ├── website_email_extractor.py   # Async contact info extractor
    └── aggregator_scrapers.py       # Aggregator site scrapers (JD, Sulekha, IndiaMART)
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| AI / LLM | Groq API (LLaMA 3 models) |
| Web Scraping | Requests, BeautifulSoup4, Playwright |
| Async Crawling | aiohttp, asyncio |
| Geocoding | Geopy (Nominatim / OpenStreetMap) |
| Retry Logic | Tenacity |
| Frontend | HTML, CSS (Inter font), Vanilla JavaScript |

---

## 🚀 Features

### 🔍 LLM-Powered Query Optimization
- User types a raw product keyword (e.g., `TDS Meter`)
- The app sends it to **Groq (LLaMA 3-8b)** which returns a smarter, business-focused search query
- Fallback to a simple keyword + location query if the API key is missing

### 🌐 DuckDuckGo Search Scraping
- Scrapes the first 10 results from DuckDuckGo's HTML interface
- Cleans tracking URLs to get real destination links
- Deduplicates results by URL

### 🏢 Aggregator Detection & Scraping
Automatically detects and specially handles these aggregator websites:
- **JustDial** — extracts multiple business listings per page
- **Sulekha** — extracts service providers
- **IndiaMART** — extracts suppliers/manufacturers
- **TradeIndia, YellowPages.in, CitySeeker** (detection supported)

### 📞 Deep Contact Info Extraction (Async)
For non-aggregator websites, crawls each page asynchronously to extract:
- **Phone numbers** — supports Indian (10-digit), international, and US formats
- **Email addresses** — regex-based with false-positive filtering
- **Physical address** — looks in `address`/`location` CSS classes and contact pages
- Falls back to the contact page if main page lacks info

### 🏆 Lead Scoring
Each lead is scored out of 100 based on data completeness:

| Data Point | Score |
|---|---|
| Has website | +15 |
| Has email | +25 |
| Has phone | +25 |
| Has address | +15 |
| Keyword in company name | +20 |

LLM post-processing re-scores and filters irrelevant results.

### 🤖 LLM Post-Processing
- Sends raw scraped leads to **Groq (LLaMA 3.1-8b-instant)**
- Cleans company names, validates contact info
- Re-scores leads and sorts them highest to lowest
- Returns strict JSON (handles markdown-wrapped responses gracefully)

### 📍 GPS-Based Location Detection
- Frontend prompts the browser for GPS coordinates
- Backend reverse-geocodes coordinates using **Geopy (Nominatim)**
- Extracts city, state, and falls back to `"India"` if unavailable

### 📥 CSV Export
- Results table can be exported as a CSV file
- Export button activates only after leads are loaded

### 🌀 Retry Logic
- All HTTP requests use **Tenacity** for automatic retries (3 attempts, exponential backoff)
- Applies to DuckDuckGo fetches, aggregator scrapes, and async website crawls

---

## 🛠️ Setup & Installation

### 1. Clone the repository
```bash
git clone <repo-url>
cd project
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers
```bash
playwright install
```

### 4. Configure environment variables
Create a `.env` file in the `project/` directory:
```
GROQ_API_KEY=your_groq_api_key_here
```
Get your free API key at [console.groq.com](https://console.groq.com)

### 5. Run the app
```bash
python app.py
```
The app runs at **http://localhost:5000**

---

## 🖥️ How to Use

1. Open `http://localhost:5000` in your browser
2. Type a product keyword (e.g., `Water Purifier`, `TDS Meter`, `Solar Panel`)
3. Click **📍 Use My Location** to auto-detect your city (optional)
4. Click **Search** and wait ~30–60 seconds for results
5. View the ranked lead table with company name, phone, email, address, website, and score
6. Click **Download CSV** to export the results

---

## 📦 Dependencies

```
Flask
playwright
beautifulsoup4
requests
python-dotenv
groq
geopy
aiohttp
tenacity
```

---

## 🔒 Input Validation & Security

- Keyword length enforced (2–100 characters)
- Dangerous characters (`<`, `>`, `"`, `'`, `;`) stripped from input
- GPS coordinates validated for range (`-90 to 90` lat, `-180 to 180` lon)
- All exceptions logged to `app.log` with full stack traces

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend dashboard |
| `POST` | `/generate-leads` | Accepts `{ keyword, location: {lat, lon} }`, returns JSON array of leads |

### Response Format
```json
[
  {
    "company_name": "ABC Water Solutions",
    "phone": "+91 98765 43210",
    "email": "info@abcwater.com",
    "location": "Pune, Maharashtra",
    "website": "https://abcwater.com",
    "score": 95
  }
]
```

---

## 📝 Logging

All events are logged to both console and `app.log`:
- Optimized search queries
- Number of raw and processed leads
- Geocoding errors
- LLM API errors
- Scraping failures per URL

---

## 🔭 Future Improvements

- [ ] Add Google Maps scraping via Playwright for richer data
- [ ] Add pagination / load more results
- [ ] Integrate LinkedIn company lookups
- [ ] Add user authentication and lead history storage
- [ ] Support multiple export formats (Excel, JSON)
- [ ] Add email verification API integration
- [ ] Deploy on cloud (Render / Railway / AWS)

---

## 👤 Author

Built as an AI-powered B2B lead generation MVP for the **Vilican** project.
