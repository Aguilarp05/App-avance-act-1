"""
Nombres EXACTOS de columnas del Excel de entrada/salida.
Ojo: algunos headers del Excel original traen un espacio al final
(p.ej. 'Nombre de la cancion ') - se respetan tal cual para no
romper la escritura de vuelta al archivo.
"""

COL_SONG = "Nombre de la canción "
COL_ARTIST = "Artista"
COL_YEAR = "Año de lanzamiento"
COL_DURATION = "Duración"
COL_BPM = "BPM"
COL_TIME_SIG = "Compás de la canción "
COL_LOUDNESS = "Volumen en db"
COL_MODE = "Modo de la cancion "
COL_DANCE = "Danceability "
COL_VALENCE = "Valance"
COL_ENERGY = "Energy"
COL_ACOUSTIC = "Acousticiness"
COL_INSTRUMENTAL = "Instrumenalness"
COL_LIVENESS = "liveness"
COL_SPEECHINESS = "speechiness"
COL_POPULARITY = "Popularity"
COL_GENRE = "Genre"
COL_LYRICS = "Lyrics"
COL_LANGUAGE = "Lenguage"

# Columna extra (no pedida originalmente) para poder auditar rapido
# que tan buenas fueron las coincidencias automaticas. Se puede borrar
# antes de entregar el trabajo si no se quiere.
COL_NOTES = "Notas_QA"

# Columnas que el script llena (en este orden se escriben al Excel)
OUTPUT_COLUMNS = [
    COL_YEAR, COL_DURATION, COL_BPM, COL_TIME_SIG, COL_LOUDNESS, COL_MODE,
    COL_DANCE, COL_VALENCE, COL_ENERGY, COL_ACOUSTIC, COL_INSTRUMENTAL,
    COL_LIVENESS, COL_SPEECHINESS, COL_POPULARITY, COL_GENRE, COL_LYRICS,
    COL_LANGUAGE, COL_NOTES,
]

REQUEST_TIMEOUT = 12
SLEEP_BETWEEN_CALLS = 0.25  # segundos, para no saturar las APIs gratuitas
SAVE_EVERY_N_ROWS = 5
FUZZY_MATCH_MIN_SCORE = 60  # 0-100, umbral minimo para aceptar una coincidencia
