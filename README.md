# app_songs_avance_act_1

Script que toma un Excel con canciones (columnas `Artista` y `Nombre de la
canción`) y llena automaticamente el resto de las columnas usando 4 APIs
gratuitas: **iTunes Search**, **ReccoBeats**, [GetSongBPM](https://getsongbpm.com)
y **LRCLIB**.

`Popularity` sale de **ReccoBeats** (su catalogo esta basado en Spotify
y su buscador ya trae ese campo 0-100 directo, sin llamada extra). Se
intento primero con la API de Spotify directamente (Client Credentials
y tambien login real de usuario via OAuth) y confirmamos que ya NO
expone ese campo para apps nuevas en ninguno de los dos casos - por
suerte ReccoBeats si lo sigue dando.

> Datos de tempo/tonalidad de cancion proporcionados por [GetSongBPM.com](https://getsongbpm.com).

## 1. Instalar (una sola vez)

```bash
cd /Users/aguilarp05/Documents/GitHub/app_songs_avance_act_1
source venv/bin/activate      # ya esta creado con todo instalado
```

## 2. (Opcional pero recomendado) API key de GetSongBPM

Sin esta key, TODO funciona excepto la columna **"Compás de la canción"**
(esa columna solo la da GetSongBPM; ninguna de las otras 3 APIs la tiene).

1. Crea cuenta en https://getsongbpm.com/api
2. Te piden un backlink a getsongbpm.com desde algun sitio tuyo (puede ser
   un repo de GitHub, un perfil, etc.)
3. Copia `.env.example` a `.env` y pega tu key:
   ```bash
   cp .env.example .env
   # edita .env y pon: GETSONGBPM_API_KEY=tu_key_aqui
   ```
4. Verifica que funciona y que los campos se leen bien:
   ```bash
   python scripts/test_getsongbpm.py "Despacito" "Luis Fonsi"
   ```

## 3. Correr el enriquecimiento

Pon tu Excel en `input/` (ya esta ahi `Avance Actividad 1.xlsx`) y corre:

```bash
python main.py
```

Esto crea `output/Avance Actividad 1_enriquecido.xlsx` con todas las
columnas llenas, y una carpeta `letras/` con un `.txt` por cancion.

> `letras/` y `output/*.xlsx` estan en `.gitignore` a proposito: el repo
> es la herramienta, no los resultados (letras completas de 100+
> canciones hacen el repo pesado). Se generan localmente corriendo el
> script, cada quien tiene los suyos.

Para probar rapido con pocas canciones primero:
```bash
python main.py --limit 5
```

Si se corta a la mitad (falla de red, Ctrl+C, etc.), simplemente vuelve a
correr `python main.py` — retoma donde se quedo, no repite trabajo ya hecho.
Para forzar que reprocese todo desde cero: `python main.py --force`.

## 4. Revisar calidad de los datos

El Excel de salida trae una columna extra `Notas_QA` (no pedida en el
formato original, se puede borrar antes de entregar) que dice, por
cancion, si alguna API no encontro nada o si el match fue dudoso (poca
coincidencia entre lo que pediste y lo que devolvio la API). Revisa esas
filas a mano.

## De donde sale cada columna

| Columna | Fuente | Notas |
|---|---|---|
| Año de lanzamiento | iTunes (respaldo: album de ReccoBeats) | |
| Duración | iTunes (respaldo: ReccoBeats) | formato `M:SS` |
| BPM | ReccoBeats (respaldo: GetSongBPM) | |
| Compás de la canción | **solo GetSongBPM** | ninguna otra fuente gratuita la tiene (ver seccion abajo) |
| Volumen en db | ReccoBeats | `loudness` |
| Modo de la canción | ReccoBeats (respaldo: GetSongBPM) | Mayor / Menor |
| Danceability, Valance, Energy, Acousticiness, Instrumenalness, liveness, speechiness | ReccoBeats | valores 0-1 |
| Popularity | **ReccoBeats** | 0-100 (su catalogo es de Spotify y si expone popularity, a diferencia de la API de Spotify directa) |
| Genre | iTunes | ReccoBeats no expone genero |
| Lyrics | LRCLIB | letra completa se guarda en `letras/`, aqui solo queda la ruta + primera linea |
| Lenguage | Detectado del texto de la letra (libreria `langdetect`) | ninguna API da idioma directo |

### Sobre Compás de la canción (cobertura limitada)

GetSongBPM es la unica fuente gratuita conocida que da compas como
dato directo, y su catalogo es bastante mas chico que el de Spotify/
Apple Music, asi que va a quedar vacio en la mayoria de las filas. Se
investigaron alternativas (Essentia/librosa para estimarlo del audio,
AcousticBrainz, APIs de pago) y ninguna es viable gratis y confiable
para este proyecto. Para las canciones que te interesen en particular,
se puede buscar a mano en:
- **Musicnotes.com** (la ficha de la partitura trae "Time Signature" sin comprar)
- **MuseScore.com** (partituras subidas por usuarios, el compas sale al inicio)
- Buscar en Google: `"cancion" "artista" time signature`

## Estructura

```
app_songs_avance_act_1/
  input/                  <- tu Excel de entrada
  output/                 <- Excel ya enriquecido
  letras/                 <- un .txt por cancion
  src/                    <- clientes de cada API + logica
  scripts/test_getsongbpm.py
  main.py
```
