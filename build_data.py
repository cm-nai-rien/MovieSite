import pandas as pd
import requests
import json
import time
import re
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV = 'chaosmovielist.csv'
OUTPUT_JSON = 'movies.json'
# PASTE YOUR KEY BELOW
TMDB_API_KEY = 'd8a1d72438cc3042bcfb451bd4ef1a07' 

def clean_title(raw_title):
    if not isinstance(raw_title, str): return ""
    if re.search(r'\d{4}', raw_title) and len(raw_title) < 15 and " " not in raw_title: return ""
    if "http" in raw_title:
        if "Lord of the Rings" in raw_title: return raw_title.split(":")[0]
        return ""
    title = raw_title.split('/')[0].strip()
    title = re.sub(r'\sS\d+(?:-S\d+)?', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\sSeason\s\d+', '', title, flags=re.IGNORECASE)
    return title.strip()

# Helper to extract standard data from API response
def extract_data(api_data, media_type_override=None):
    poster = api_data.get('poster_path')
    if not poster: return None

    # Determine Type (Movie vs TV)
    m_type = media_type_override or api_data.get('media_type', 'movie')
    
    # Determine Year
    date = api_data.get('release_date') or api_data.get('first_air_date')
    year = date[:4] if date else "Unknown"

    # Determine Country (Try origin_country first, then production_countries)
    country = "Unknown"
    if 'origin_country' in api_data and api_data['origin_country']:
        country = api_data['origin_country'][0]
    elif 'production_countries' in api_data and api_data['production_countries']:
        country = api_data['production_countries'][0]['iso_3166_1']
    elif 'original_language' in api_data:
        country = api_data['original_language'].upper() # Fallback

    return {
        "poster": f"https://image.tmdb.org/t/p/w500{poster}",
        "type": m_type,
        "year": year,
        "country": country
    }

def get_data_from_link(tmdb_link):
    match = re.search(r'themoviedb\.org/(movie|tv)/(\d+)', tmdb_link)
    if match:
        media_type = match.group(1)
        tmdb_id = match.group(2)
        api_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_API_KEY}"
        try:
            response = requests.get(api_url)
            data = response.json()
            return extract_data(data, media_type)
        except Exception as e:
            print(f"   [!] API Error: {e}")
    return None

def get_data_from_search(title):
    search_url = f"https://api.themoviedb.org/3/search/multi?query={title}&api_key={TMDB_API_KEY}"
    try:
        response = requests.get(search_url)
        data = response.json()
        if data.get('results'):
            return extract_data(data['results'][0])
    except:
        pass
    return None

# --- MAIN EXECUTION ---

try:
    try:
        df = pd.read_csv(INPUT_CSV, on_bad_lines='skip', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(INPUT_CSV, on_bad_lines='skip', encoding='gbk')
except:
    print("Error reading CSV.")
    exit()

movie_list = []
df = df.fillna("") 

print(f"Processing {len(df)} items (Fetching Country, Year, Type)...")

for index, row in df.iterrows():
    raw_name = str(row.get('Name', ''))
    search_title = clean_title(raw_name)
    
    if not search_title or len(search_title) < 2:
        raw_name = str(row.iloc[0]) 
        search_title = clean_title(raw_name)

    if not search_title: continue

    tmdb_data = None
    found_link = False
    
    # Smart Scan for Link
    for col_name in df.columns:
        cell_value = str(row[col_name])
        if "themoviedb.org" in cell_value:
            print(f"[{search_title}] 🌟 Link found...")
            tmdb_data = get_data_from_link(cell_value)
            found_link = True
            break
    
    # Search if no link
    if not tmdb_data:
        tmdb_data = get_data_from_search(search_title)

    # Process Review/Date/Rating
    review = str(row.get('Notes', ''))
    if len(review) < 5 and 'Extra' in row: review = str(row.get('Extra', ''))
    
    date_str = str(row.get('Date', ''))
    display_date = date_str
    try:
        dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
        sortable_date = dt.strftime("%Y-%m-%d")
    except:
        sortable_date = "0000-00-00"
        
    rating = str(row.get('Rate', ''))
    if rating == "": rating = str(row.get('Rate 5/5', ''))

    if tmdb_data:
        print(f"OK: {search_title} | {tmdb_data['country']} | {tmdb_data['year']}")
        movie_list.append({
            "title": search_title,
            "date_display": display_date,
            "date_sort": sortable_date,
            "review": review,
            "rating": rating,
            # NEW FIELDS
            "poster": tmdb_data['poster'],
            "type": tmdb_data['type'],
            "year": tmdb_data['year'],
            "country": tmdb_data['country']
        })
    else:
        print(f"Fail: {search_title}")

    time.sleep(0.1) 

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(movie_list, f, indent=4, ensure_ascii=False)

print(f"Done! Saved {len(movie_list)} movies.")