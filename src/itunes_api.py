"""Cliente de iTunes Search API (sin API key)."""
import requests

from src.config import REQUEST_TIMEOUT
from src.utils import best_match

SEARCH_URL = "https://itunes.apple.com/search"


def search_track(artist: str, song: str, country: str = "US", limit: int = 15):
    """Busca la cancion en iTunes y regresa el resultado que mejor
    coincide con artista+cancion, o None si no hay nada aceptable."""
    params = {
        "term": f"{artist} {song}",
        "entity": "song",
        "limit": limit,
        "country": country,
    }
    try:
        r = requests.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return None, 0

    results = data.get("results", [])
    if not results:
        return None, 0

    best, score = best_match(
        artist, song, results,
        get_artist=lambda t: t.get("artistName", ""),
        get_song=lambda t: t.get("trackName", ""),
    )
    return best, score


def extract_fields(track: dict) -> dict:
    """Convierte el JSON de iTunes en los campos que nos interesan."""
    if not track:
        return {}

    year = None
    release_date = track.get("releaseDate")
    if release_date:
        year = release_date[:4]

    duration_str = None
    millis = track.get("trackTimeMillis")
    if millis:
        total_seconds = int(millis) // 1000
        minutes, seconds = divmod(total_seconds, 60)
        duration_str = f"{minutes}:{seconds:02d}"

    return {
        "year": year,
        "duration": duration_str,
        "duration_seconds": (millis // 1000) if millis else None,
        "genre": track.get("primaryGenreName"),
        "itunes_artist": track.get("artistName"),
        "itunes_track": track.get("trackName"),
        "album": track.get("collectionName"),
    }
