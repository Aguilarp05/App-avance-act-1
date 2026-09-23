"""Utilidades compartidas: normalizacion de texto y fuzzy matching."""
import re
import unicodedata

from rapidfuzz import fuzz


def strip_accents(text: str) -> str:
    """Quita acentos/diacriticos. 'Tití' -> 'Titi'. Util porque la
    busqueda de ReccoBeats no encuentra nada si el texto lleva acentos."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def sanitize_filename(text: str, max_len: int = 80) -> str:
    """Convierte un string en un nombre de archivo seguro."""
    text = strip_accents(text)
    text = re.sub(r"[^\w\s-]", "", text).strip()
    text = re.sub(r"[\s]+", "_", text)
    return text[:max_len] or "sin_nombre"


def similarity(a: str, b: str) -> float:
    """Score de parecido 0-100 entre dos strings, insensible a mayus/acentos."""
    a = strip_accents(str(a or "")).lower().strip()
    b = strip_accents(str(b or "")).lower().strip()
    if not a or not b:
        return 0.0
    return fuzz.token_sort_ratio(a, b)


def best_match(target_artist: str, target_song: str, candidates, get_artist, get_song):
    """
    Recibe una lista de candidatos y funciones para extraer artista/cancion
    de cada uno. Regresa (mejor_candidato, score) combinando el parecido
    de artista + cancion, o (None, 0) si la lista esta vacia.
    """
    best = None
    best_score = -1.0
    for c in candidates:
        s_artist = similarity(target_artist, get_artist(c))
        s_song = similarity(target_song, get_song(c))
        score = (s_artist * 0.5) + (s_song * 0.5)
        if score > best_score:
            best_score = score
            best = c
    return best, best_score
