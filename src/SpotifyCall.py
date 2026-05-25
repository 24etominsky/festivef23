import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import requests

load_dotenv()


def get_genres_lastfm(artist_name, api_key):
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.getTopTags",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json"
    }
    try:
        res = requests.get(url, params=params, timeout=5).json()
        tags = [t["name"] for t in res.get("toptags", {}).get("tag", [])]
        return tags[:5]
    except Exception:
        return []


def compile_genres(list_of_artists):
    key = os.getenv("FM_API_KEY")

    def fetch(artist):
        return get_genres_lastfm(artist, key)

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(fetch, list_of_artists))

    FILTERED = {
        "seen live", "favorites", "favorite", "love",
        "pop", "electronic", "alternative", "rock",
        "female vocalists", "singer-songwriter",
        "american", "british", "australian", "experimental", "folk",
    }

    genres = []
    for g in results:
        genres.extend(
            tag for tag in g
            if "indie" not in tag.lower() and tag.lower() not in FILTERED
        )
    return genres


def get_spotify_url(artist_name, sp):
    try:
        result = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
        items = result["artists"]["items"]
        if items:
            return items[0]["external_urls"]["spotify"]
    except Exception:
        pass
    return None


def compare_genres(user_genres, artist_names, sp=None):
    fm_key = os.getenv("FM_API_KEY")

    def process_artist(artist):
        festival_genres = get_genres_lastfm(artist, fm_key)
        matched = []
        score = 0
        for genre in festival_genres:
            if genre in user_genres:
                score += user_genres.count(genre)
                if genre not in matched:
                    matched.append(genre)
        spotify_url = get_spotify_url(artist, sp) if sp else None
        return {
            "name": artist,
            "score": score,
            "matched_genres": matched[:3],
            "spotify_url": spotify_url,
        }

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_artist, artist_names))

    return sorted(results, key=lambda x: x["score"], reverse=True)
