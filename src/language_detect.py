"""Deteccion de idioma a partir de la letra (LRCLIB no da idioma directo)."""
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0  # resultados reproducibles

LANG_NAMES = {
    "es": "Español",
    "en": "Inglés",
    "pt": "Portugués",
    "fr": "Francés",
    "it": "Italiano",
    "de": "Alemán",
    "ca": "Catalán",
}


def detect_language(text: str):
    text = (text or "").strip()
    if len(text) < 15:
        return None
    try:
        code = detect(text)
    except LangDetectException:
        return None
    return LANG_NAMES.get(code, code)
