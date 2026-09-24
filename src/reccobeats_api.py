"""
Cliente de ReccoBeats (sin API key).

Nota importante descubierta probando la API en vivo:
- El endpoint /v1/track/search solo funciona bien buscando por TITULO
  de la cancion (sin el artista pegado en el mismo texto: pedir
  "Despacito Luis Fonsi" regresa 0 resultados, pero "Despacito" solo
  regresa 200). Por eso aqui se busca solo el titulo y luego se filtra
  el artista correcto nosotros mismos (fuzzy match) entre los resultados.
- Tampoco tolera bien los acentos ("Tití" no encuentra nada, "Titi" si),
  asi que el texto de busqueda se manda sin acentos.
- /v1/track/{id}/audio-features NO incluye compas (time signature) ni
  popularity.
- PERO el resultado de /v1/track/search SI trae "popularity" (0-100,
  igual que Spotify) y "durationMs" directo en cada track - no hacia
  falta Spotify para Popularity, solo no lo estabamos leyendo. Y
  /v1/track/{id}/album da "releaseDate" como respaldo del Año cuando
  iTunes no tiene la cancion.
"""
import requests

from src.config import REQUEST_TIMEOUT, FUZZY_MATCH_MIN_SCORE
from src.utils import strip_accents, best_match

BASE_URL = "https://api.reccobeats.com/v1"
SEARCH_URL = f"{BASE_URL}/track/search"
MAX_PAGES = 3  # 3 paginas x 50 = hasta 150 resultados revisados


def _get_artists_str(track: dict) -> str:
    return ", ".join(a.get("name", "") for a in track.get("artists", []))


def search_track(artist: str, song: str):
    """Busca la cancion por titulo (paginando) y filtra por el artista
    mas parecido. Regresa (track_dict, score) o (None, 0)."""
    query = strip_accents(song)
    best_overall = None
    best_score = -1.0

    for page in range(MAX_PAGES):
        params = {"searchText": query, "size": 50, "page": page}
        try:
            r = requests.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError):
            break

        content = data.get("content", [])
        if not content:
            break

        candidate, score = best_match(
            artist, song, content,
            get_artist=_get_artists_str,
            get_song=lambda t: t.get("trackTitle", ""),
        )
        if score > best_score:
            best_overall, best_score = candidate, score

        # ya encontramos algo muy bueno, no hace falta seguir paginando
        if best_score >= 90:
            break
        if page + 1 >= data.get("totalPages", 1):
            break

    if best_overall is None or best_score < FUZZY_MATCH_MIN_SCORE:
        return None, best_score if best_overall else 0
    return best_overall, best_score


def get_audio_features(track_id: str):
    """GET /v1/track/{id}/audio-features"""
    try:
        r = requests.get(
            f"{BASE_URL}/track/{track_id}/audio-features",
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        return None


def get_release_year(track_id: str):
    """GET /v1/track/{id}/album - regresa el anio de lanzamiento (str) o None."""
    try:
        r = requests.get(f"{BASE_URL}/track/{track_id}/album", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return None

    albums = data.get("content", [])
    if not albums:
        return None
    release_date = albums[0].get("releaseDate")
    return release_date[:4] if release_date else None


def extract_track_fields(track: dict) -> dict:
    """Campos que ya vienen en el resultado de search_track (sin llamadas
    extra): popularity y duracion."""
    if not track:
        return {}
    duration_ms = track.get("durationMs")
    duration_str = None
    if duration_ms:
        total_seconds = int(duration_ms) // 1000
        minutes, seconds = divmod(total_seconds, 60)
        duration_str = f"{minutes}:{seconds:02d}"
    return {
        "popularity": track.get("popularity"),
        "duration": duration_str,
    }


def extract_fields(features: dict) -> dict:
    if not features:
        return {}
    mode_val = features.get("mode")
    modo = None
    if mode_val is not None:
        modo = "Mayor" if int(mode_val) == 1 else "Menor"

    def r(key, digits):
        val = features.get(key)
        return round(val, digits) if val is not None else None

    return {
        "bpm": r("tempo", 1),
        "loudness": r("loudness", 2),
        "mode": modo,
        "danceability": r("danceability", 3),
        "valence": r("valence", 3),
        "energy": r("energy", 3),
        "acousticness": r("acousticness", 3),
        "instrumentalness": r("instrumentalness", 3),
        "liveness": r("liveness", 3),
        "speechiness": r("speechiness", 3),
    }
