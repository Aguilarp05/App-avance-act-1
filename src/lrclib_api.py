"""Cliente de LRCLIB (sin API key)."""
import requests

from src.config import REQUEST_TIMEOUT
from src.utils import best_match

SEARCH_URL = "https://lrclib.net/api/search"


def search_lyrics(artist: str, song: str):
    """Busca la letra y regresa (resultado_dict, score) o (None, 0)."""
    params = {"track_name": song, "artist_name": artist}
    try:
        r = requests.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        results = r.json()
    except (requests.RequestException, ValueError):
        return None, 0

    if not results:
        return None, 0

    best, score = best_match(
        artist, song, results,
        get_artist=lambda t: t.get("artistName", ""),
        get_song=lambda t: t.get("trackName", ""),
    )
    return best, score


def extract_fields(result: dict) -> dict:
    if not result:
        return {}
    return {
        "instrumental": result.get("instrumental", False),
        "plain_lyrics": result.get("plainLyrics") or "",
        "synced_lyrics": result.get("syncedLyrics") or "",
    }
