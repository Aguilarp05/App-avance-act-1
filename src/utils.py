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


# Caracteres que a veces se usan por error en vez de un apostrofe recto
# (comun en textos copiados de Word/Notas/iOS: "Let´s", "I Don´t",
# "Isn´t"). Si se dejan asi, las busquedas en las APIs no encuentran
# nada aunque la cancion exista, porque el titulo real usa "'".
_APOSTROPHE_LOOKALIKES = "´`’‘"


def normalize_query_text(text: str) -> str:
    """Limpia un texto ANTES de mandarlo a buscar a cualquier API:
    normaliza apostrofes raros a uno recto y colapsa espacios."""
    if not text:
        return ""
    for ch in _APOSTROPHE_LOOKALIKES:
        text = text.replace(ch, "'")
    return re.sub(r"\s+", " ", text).strip()


def sanitize_filename(text: str, max_len: int = 80) -> str:
    """Convierte un string en un nombre de archivo seguro."""
    text = strip_accents(text)
    text = re.sub(r"[^\w\s-]", "", text).strip()
    text = re.sub(r"[\s]+", "_", text)
    return text[:max_len] or "sin_nombre"


def similarity(a: str, b: str) -> float:
    """Score de parecido 0-100 entre dos strings, insensible a mayus/acentos.

    Usa WRatio (rapidfuzz) en vez de un simple token_sort_ratio porque
    maneja mucho mejor los casos de "artista principal + featuring"
    (ej. 'Morat' vs 'Morat & Silvestre Dangond' -> ~90) sin dejar de
    castigar fuerte artistas que de plano no tienen nada que ver
    (ej. 'Humbe' vs 'Chino & Nacho' -> ~26)."""
    a = strip_accents(str(a or "")).lower().strip()
    b = strip_accents(str(b or "")).lower().strip()
    if not a or not b:
        return 0.0
    return fuzz.WRatio(a, b)


# Pisos minimos de parecido para aceptar un candidato. Se exigen los
# DOS (artista Y titulo) por separado -- no basta con que el promedio
# salga alto. Sin esto pasaban cosas como:
#   - iTunes: "Mac Miller - 2009" no estaba en los resultados, pero SI
#     "Mac Miller - Circles" (artista=100%, titulo=0%); el promedio
#     (50%) se aceptaba con solo la nota de "dudoso", mostrando la
#     duracion de la cancion equivocada.
#   - ReccoBeats: "Mac Miller" vs "Hate Gallery" (artista totalmente
#     distinto) dio 54.5% de parecido por pura coincidencia de letras,
#     pasando el filtro viejo de 45%.
# Calibrado con casos reales de esta sesion:
#   - 'Morat' vs 'Morat & Silvestre Dangond' (featuring real) -> 90
#   - 'Humbe' vs 'Chino & Nacho' (artista equivocado) -> 26
#   - 'Mac Miller' vs 'Hate Gallery' (coincidencia de letras) -> 54.5
MIN_ARTIST_SCORE = 60
MIN_SONG_SCORE = 50


def best_match(target_artist: str, target_song: str, candidates, get_artist, get_song):
    """
    Recibe una lista de candidatos y funciones para extraer artista/cancion
    de cada uno. Regresa (mejor_candidato, score) combinando el parecido
    de artista + cancion, o (None, 0) si ningun candidato tiene AMBOS
    (artista y titulo) lo bastante parecidos -- evita quedarse con otra
    cancion del mismo artista, o con la cancion correcta de otro artista.
    """
    best = None
    best_score = -1.0
    for c in candidates:
        s_artist = similarity(target_artist, get_artist(c))
        if s_artist < MIN_ARTIST_SCORE:
            continue  # otro artista, no es la cancion
        s_song = similarity(target_song, get_song(c))
        if s_song < MIN_SONG_SCORE:
            continue  # mismo artista pero otra cancion
        score = (s_artist * 0.5) + (s_song * 0.5)
        if score > best_score:
            best_score = score
            best = c
    if best is None:
        return None, 0
    return best, best_score
