"""
One-time script to enrich movies.json with TMDB public ratings (vote_average).
Only fetches for movies missing tmdb_rating.
"""
import json
import requests
import time

TMDB_API_KEY = 'd8a1d72438cc3042bcfb451bd4ef1a07'
JSON_FILE = 'movies.json'

with open(JSON_FILE, encoding='utf-8') as f:
    movies = json.load(f)

needs_enrichment = [m for m in movies if m.get('poster') and 'tmdb_rating' not in m]
print(f"Fetching TMDB ratings for {len(needs_enrichment)} movies...")

for i, movie in enumerate(needs_enrichment):
    title = movie['title']
    year = movie.get('year', '')
    query = requests.utils.quote(title)
    url = f"https://api.themoviedb.org/3/search/multi?query={query}&api_key={TMDB_API_KEY}"
    if year and year != 'Unknown':
        url += f"&year={year}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        results = data.get('results', [])
        if results:
            vote = results[0].get('vote_average')
            movie['tmdb_rating'] = round(vote, 1) if vote else None
        else:
            movie['tmdb_rating'] = None
    except Exception as e:
        movie['tmdb_rating'] = None
        print(f"  Error for {title}: {e}")

    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(needs_enrichment)} done...")
    time.sleep(0.12)

with open(JSON_FILE, 'w', encoding='utf-8') as f:
    json.dump(movies, f, indent=4, ensure_ascii=False)

print(f"Done! Enriched {len(needs_enrichment)} movies.")
