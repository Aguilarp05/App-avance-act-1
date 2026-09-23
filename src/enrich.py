"""Orquesta las 4 APIs para una sola cancion y regresa un dict listo
para volcar en las columnas del Excel."""
import os
import time

from src import getsongbpm_api, itunes_api, lrclib_api, reccobeats_api
from src.config import (
    COL_ACOUSTIC, COL_BPM, COL_DANCE, COL_DURATION, COL_ENERGY, COL_GENRE,
    COL_INSTRUMENTAL, COL_LANGUAGE, COL_LIVENESS, COL_LOUDNESS, COL_LYRICS,
    COL_MODE, COL_NOTES, COL_POPULARITY, COL_SPEECHINESS, COL_TIME_SIG,
    COL_VALENCE, COL_YEAR, SLEEP_BETWEEN_CALLS,
)
from src.language_detect import detect_language
from src.utils import sanitize_filename


def enrich_song(artist: str, song: str, row_index: int, letras_dir: str) -> dict:
    result = {col: None for col in [
        COL_YEAR, COL_DURATION, COL_BPM, COL_TIME_SIG, COL_LOUDNESS, COL_MODE,
        COL_DANCE, COL_VALENCE, COL_ENERGY, COL_ACOUSTIC, COL_INSTRUMENTAL,
        COL_LIVENESS, COL_SPEECHINESS, COL_POPULARITY, COL_GENRE, COL_LYRICS,
        COL_LANGUAGE,
    ]}
    notes = []

    # --- iTunes: metadata basica ---
    itunes_track, itunes_score = itunes_api.search_track(artist, song)
    time.sleep(SLEEP_BETWEEN_CALLS)
    # Artista/cancion "limpios" para las busquedas siguientes: si iTunes
    # encontro un match CONFIABLE (>=80%), se usa el nombre oficial que
    # el confirmo en vez del texto crudo del Excel (que a veces trae
    # typos/comillas raras que hacen fallar la busqueda en otras APIs).
    # Si el match de iTunes fue dudoso o no encontro nada, se sigue
    # usando el texto original tal cual, para no propagar un error.
    search_artist, search_song = artist, song
    if itunes_track:
        fields = itunes_api.extract_fields(itunes_track)
        result[COL_YEAR] = fields.get("year")
        result[COL_DURATION] = fields.get("duration")
        result[COL_GENRE] = fields.get("genre")
        if itunes_score < 80:
            notes.append(f"iTunes: match dudoso ({itunes_score:.0f}%)")
        else:
            search_artist = fields.get("itunes_artist") or artist
            search_song = fields.get("itunes_track") or song
    else:
        notes.append("iTunes: no encontrado")

    # --- ReccoBeats: audio features (fuente principal de BPM/modo/etc) ---
    recco_track, recco_score = reccobeats_api.search_track(search_artist, search_song)
    time.sleep(SLEEP_BETWEEN_CALLS)
    if recco_track:
        features = reccobeats_api.get_audio_features(recco_track["id"])
        time.sleep(SLEEP_BETWEEN_CALLS)
        fields = reccobeats_api.extract_fields(features)
        result[COL_BPM] = fields.get("bpm")
        result[COL_LOUDNESS] = fields.get("loudness")
        result[COL_MODE] = fields.get("mode")
        result[COL_DANCE] = fields.get("danceability")
        result[COL_VALENCE] = fields.get("valence")
        result[COL_ENERGY] = fields.get("energy")
        result[COL_ACOUSTIC] = fields.get("acousticness")
        result[COL_INSTRUMENTAL] = fields.get("instrumentalness")
        result[COL_LIVENESS] = fields.get("liveness")
        result[COL_SPEECHINESS] = fields.get("speechiness")
        if recco_score < 80:
            notes.append(f"ReccoBeats: match dudoso ({recco_score:.0f}%)")
    else:
        notes.append("ReccoBeats: no encontrado (sin audio features)")

    # --- GetSongBPM: BPM/compas/modo de respaldo (compas SOLO sale de aqui) ---
    if getsongbpm_api.is_enabled():
        gsbpm = getsongbpm_api.search_song(search_artist, search_song)
        time.sleep(SLEEP_BETWEEN_CALLS)
        if gsbpm:
            fields = getsongbpm_api.extract_fields(gsbpm)
            result[COL_TIME_SIG] = fields.get("time_sig")
            if result[COL_BPM] is None:
                result[COL_BPM] = fields.get("bpm")
            if result[COL_MODE] is None:
                result[COL_MODE] = fields.get("mode")
            if result[COL_DANCE] is None:
                result[COL_DANCE] = fields.get("danceability")
            if result[COL_ACOUSTIC] is None:
                result[COL_ACOUSTIC] = fields.get("acousticness")
        else:
            notes.append("GetSongBPM: no encontrado")
    else:
        notes.append("GetSongBPM: sin API key (Compas no se pudo llenar)")

    # --- LRCLIB: letra + idioma ---
    lyrics_result, lyrics_score = lrclib_api.search_lyrics(search_artist, search_song)
    time.sleep(SLEEP_BETWEEN_CALLS)
    if lyrics_result:
        fields = lrclib_api.extract_fields(lyrics_result)
        if fields.get("instrumental"):
            result[COL_LYRICS] = "Instrumental (sin letra)"
        elif fields.get("plain_lyrics"):
            fname = f"{row_index:03d}_{sanitize_filename(artist)}_{sanitize_filename(song)}.txt"
            fpath = os.path.join(letras_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(fields["plain_lyrics"])
            preview = fields["plain_lyrics"].splitlines()[0][:80]
            result[COL_LYRICS] = f"letras/{fname} | \"{preview}...\""
            result[COL_LANGUAGE] = detect_language(fields["plain_lyrics"])
        else:
            notes.append("LRCLIB: encontrado pero sin texto de letra")
        if lyrics_score < 70:
            notes.append(f"LRCLIB: match dudoso ({lyrics_score:.0f}%)")
    else:
        notes.append("LRCLIB: letra no encontrada")

    # Compas: si ninguna fuente lo dio (GetSongBPM es la unica que lo
    # tiene y su catalogo es chico), se asume "4/4" -- es el compas de
    # ~85-90% de la musica comercial pop/rock/latina. Se marca claro
    # como asumido, no como dato confirmado por una API.
    if result[COL_TIME_SIG] is None:
        result[COL_TIME_SIG] = "4/4 (asumido)"
        notes.append("Compas: asumido 4/4 (no confirmado por GetSongBPM)")

    # Popularity: se probo Spotify (Client Credentials Y login de usuario
    # real via OAuth) y confirmamos que ya no expone ese campo para apps
    # nuevas en ninguno de los dos casos. Ninguna de las 4 APIs originales
    # lo tiene tampoco. Se deja en blanco a proposito.
    notes.append("Popularity: no disponible (Spotify ya no expone ese campo para apps nuevas)")

    result[COL_NOTES] = " | ".join(notes)
    return result
