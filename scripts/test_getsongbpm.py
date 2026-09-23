"""
Prueba rapida y aislada de GetSongBPM una vez que tengas tu API key en .env.
Imprime el JSON crudo para poder confirmar los nombres de campo reales
(el modulo src/getsongbpm_api.py ya intenta varios alias, pero si algo
no calza, aqui se ve exactamente que trae la respuesta).

Uso:
    python scripts/test_getsongbpm.py "Despacito" "Luis Fonsi"
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from src import getsongbpm_api  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('Uso: python scripts/test_getsongbpm.py "cancion" "artista"')
        sys.exit(1)

    if not getsongbpm_api.is_enabled():
        print("No hay GETSONGBPM_API_KEY en .env. Copia .env.example a .env y ponla ahi.")
        sys.exit(1)

    song, artist = sys.argv[1], sys.argv[2]
    raw = getsongbpm_api.search_song(artist, song)
    print("--- JSON crudo de GetSongBPM ---")
    print(json.dumps(raw, indent=2, ensure_ascii=False))
    print("\n--- Campos que el script extraeria ---")
    print(json.dumps(getsongbpm_api.extract_fields(raw), indent=2, ensure_ascii=False))
