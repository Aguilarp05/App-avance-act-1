"""
Llena las columnas de audio/metadata/letras de un Excel de canciones
usando iTunes Search, ReccoBeats, GetSongBPM y LRCLIB.

Uso:
    python main.py
    python main.py --input input/mi_archivo.xlsx --output output/salida.xlsx
    python main.py --force        (reprocesa todo, ignora avance previo)
    python main.py --limit 5      (solo procesa las primeras 5 filas, para probar rapido)
"""
import argparse
import glob
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from src.config import (
    COL_ARTIST, COL_GENRE, COL_NOTES, COL_SONG, OUTPUT_COLUMNS,
    SAVE_EVERY_N_ROWS,
)
from src.enrich import enrich_song

load_dotenv()

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LETRAS_DIR = os.path.join(PROJECT_DIR, "letras")


def find_default_input():
    candidates = glob.glob(os.path.join(PROJECT_DIR, "input", "*.xlsx"))
    candidates = [c for c in candidates if not os.path.basename(c).startswith("~$")]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) == 0:
        return None
    return candidates[0]  # si hay varios, toma el primero (se avisa en main)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=None, help="Excel de entrada (default: unico .xlsx en input/)")
    parser.add_argument("--output", default=None, help="Excel de salida (default: output/<mismo nombre>_enriquecido.xlsx)")
    parser.add_argument("--force", action="store_true", help="Reprocesa todas las filas aunque ya tengan datos")
    parser.add_argument("--limit", type=int, default=None, help="Solo procesar las primeras N filas (para pruebas)")
    args = parser.parse_args()

    input_path = args.input or find_default_input()
    if not input_path or not os.path.exists(input_path):
        print("No encontre el Excel de entrada. Pon uno en input/ o usa --input ruta/al/archivo.xlsx")
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(PROJECT_DIR, "output", f"{base}_enriquecido.xlsx")

    os.makedirs(LETRAS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Si ya existe una corrida previa del OUTPUT, retomamos desde ahi
    # (asi si se corta a la mitad de 200 canciones no hay que repetir todo).
    if not args.force and os.path.exists(output_path):
        print(f"Encontre una corrida previa en {output_path}, retomando avance...")
        df = pd.read_excel(output_path)
    else:
        df = pd.read_excel(input_path)

    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = None
        # dtype 'object' para poder mezclar numeros/texto/None sin que
        # pandas truene al escribir valores de distinto tipo en la celda
        df[col] = df[col].astype(object).where(df[col].notna(), None)

    if COL_SONG not in df.columns or COL_ARTIST not in df.columns:
        print(f"El Excel debe tener las columnas '{COL_SONG}' y '{COL_ARTIST}'.")
        sys.exit(1)

    total = len(df) if args.limit is None else min(args.limit, len(df))
    pendientes = 0
    procesadas = 0

    for i in tqdm(range(total), desc="Enriqueciendo canciones"):
        row = df.iloc[i]
        ya_hecho = not args.force and pd.notna(row.get(COL_GENRE)) and pd.notna(row.get(COL_NOTES))
        if ya_hecho:
            pendientes += 0
            continue

        artist = str(row[COL_ARTIST]).strip()
        song = str(row[COL_SONG]).strip()
        if not artist or artist == "nan" or not song or song == "nan":
            continue

        try:
            data = enrich_song(artist, song, i, LETRAS_DIR)
        except Exception as e:  # nunca tumbar la corrida completa por una cancion
            data = {COL_NOTES: f"ERROR procesando esta fila: {e}"}

        for col, val in data.items():
            df.at[i, col] = val
        procesadas += 1

        if procesadas % SAVE_EVERY_N_ROWS == 0:
            df.to_excel(output_path, index=False)

    df.to_excel(output_path, index=False)
    print(f"\nListo. {procesadas} canciones procesadas en esta corrida.")
    print(f"Excel guardado en: {output_path}")
    print(f"Letras guardadas en: {LETRAS_DIR}/")
    print(f"Revisa la columna '{COL_NOTES}' para ver matches dudosos o fuentes que no encontraron nada.")


if __name__ == "__main__":
    main()
