"""
Cliente de GetSongBPM (SI requiere API key gratuita, ver README).

OJO: como no tenemos todavia una key para probar en vivo, el parseo
de la respuesta esta hecho de forma defensiva (intenta varios nombres
de campo posibles segun la documentacion publica de la API) y nunca
truena el script si algo no calza. En cuanto tengas tu key, corre
`python scripts/test_getsongbpm.py "cancion" "artista"` para ver el
JSON real y, si algun campo no se esta leyendo bien, se ajusta aqui
en dos lineas.
"""
import os

import requests

from src.config import REQUEST_TIMEOUT

BASE_URL = "https://api.getsong.co"


def _get_api_key():
    return os.environ.get("GETSONGBPM_API_KEY", "").strip()


def is_enabled() -> bool:
    return bool(_get_api_key())


def search_song(artist: str, song: str):
    """Busca la cancion. Regresa el primer resultado (dict) o None."""
    api_key = _get_api_key()
    if not api_key:
        return None

    lookup = f"song:{song} artist:{artist}"
    params = {
        "api_key": api_key,
        "type": "both",
        "lookup": lookup,
        "limit": 1,
    }
    try:
        r = requests.get(f"{BASE_URL}/search/", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return None

    results = data.get("search")
    if not results or not isinstance(results, list):
        return None
    return results[0]


def _first_present(d: dict, keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, "", "-1"):
            return d[k]
    return default


def extract_fields(song: dict) -> dict:
    """Parseo defensivo: la API documenta 'tempo', 'time_sig' y 'key_of'
    (ej. 'F#m' = F# menor, 'C' = C mayor) pero se dejan alias por si
    la respuesta real trae otro nombre."""
    if not song:
        return {}

    bpm = _first_present(song, ["tempo", "bpm"])
    if bpm is not None:
        try:
            bpm = round(float(bpm), 1)
        except (TypeError, ValueError):
            pass

    time_sig_raw = _first_present(song, ["time_sig", "timeSignature", "time_signature"])
    time_sig = None
    if time_sig_raw is not None:
        time_sig = str(time_sig_raw)
        if "/" not in time_sig:
            time_sig = f"{time_sig}/4"

    key_of = _first_present(song, ["key_of", "keyOf", "key"])
    modo = None
    if key_of:
        key_of = str(key_of)
        modo = "Menor" if key_of.strip().lower().endswith("m") else "Mayor"

    return {
        "bpm": bpm,
        "time_sig": time_sig,
        "mode": modo,
        "key_of_raw": key_of,
    }
