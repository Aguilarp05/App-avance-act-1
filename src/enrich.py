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
from src.utils import normalize_query_text, sanitize_filename


def enrich_song(artist: str, song: str, row_index: int, letras_dir: str) -> dict:
    result = {col: None for col in [
        COL_YEAR, COL_DURATION, COL_BPM, COL_TIME_SIG, COL_LOUDNESS, COL_MODE,
        COL_DANCE, COL_VALENCE, COL_ENERGY, COL_ACOUSTIC, COL_INSTRUMENTAL,
        COL_LIVENESS, COL_SPEECHINESS, COL_POPULARITY, COL_GENRE, COL_LYRICS,
        COL_LANGUAGE,
    ]}
    notes = []

    # Limpia apostrofes raros (´ en vez de ') ANTES de buscar en
    # cualquier API - varios titulos del Excel los traen y eso hacia
    # fallar la busqueda aunque la cancion si existiera.
    artist = normalize_query_text(artist)
    song = normalize_query_text(song)

    # Artista/cancion "limpios" para las busquedas siguientes: si iTunes
    # (o, en su defecto, ReccoBeats) encuentra un match CONFIABLE
    # (>=80%), se usa el nombre oficial que confirmo en vez del texto
    # crudo del Excel. Si ninguno confia, se sigue usando el texto
    # original, para no propagar un error a las demas fuentes.
    search_artist, search_song = artist, song

    # --- iTunes: metadata basica ---
    itunes_track, itunes_score = itunes_api.search_track(artist, song)
    time.sleep(SLEEP_BETWEEN_CALLS)
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
        # Si iTunes no dio un nombre oficial confiable pero ReccoBeats si
        # encontro la cancion con confianza, tambien sirve como fuente
        # de nombre "limpio" para GetSongBPM/LRCLIB mas adelante.
        if search_artist == artist and recco_score >= 80:
            artists_str = ", ".join(a.get("name", "") for a in recco_track.get("artists", []))
            search_artist = artists_str or artist
            search_song = recco_track.get("trackTitle") or song
        # popularity y duracion ya vienen en el resultado de search, sin
        # llamada extra
        track_fields = reccobeats_api.extract_track_fields(recco_track)
        result[COL_POPULARITY] = track_fields.get("popularity")
        if result[COL_DURATION] is None:
            result[COL_DURATION] = track_fields.get("duration")

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

        # Año de respaldo cuando iTunes no tiene la cancion (llamada extra
        # solo cuando de verdad hace falta)
        if result[COL_YEAR] is None:
            year = reccobeats_api.get_release_year(recco_track["id"])
            time.sleep(SLEEP_BETWEEN_CALLS)
            if year:
                result[COL_YEAR] = year

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

    if result[COL_POPULARITY] is None:
        notes.append("Popularity: no disponible (cancion no encontrada en ReccoBeats)")

    result[COL_NOTES] = " | ".join(notes)
    return result
