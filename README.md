# Video Reducer

Riduce le dimensioni dei file video tramite codec ad alta efficienza (H.265/HEVC, AV1), mantenendo la qualità.

Funziona su **Windows**, **macOS** e **Linux** — da riga di comando o con interfaccia grafica.

![icon](icon.png)

## Funzionalità

- **Scansione e mappatura** — rileva tutti i file video in una cartella e li categorizza automaticamente:
  - `heavy_codec` — codec pesanti (MJPEG, ProRes, DNxHD, XAVC, ecc.)
  - `large_file` — file sopra una soglia configurabile (default 500 MB)
  - `high_bitrate` — bitrate sproporzionato rispetto alla risoluzione
  - `not_efficient` — qualsiasi codec non già ad alta efficienza
- **5 preset di conversione**:
  - `lossy` — H.265 CRF 23 (buona qualità, massima riduzione)
  - `lossy_light` — H.265 CRF 18 (qualità quasi identica all'originale)
  - `lossless` — H.265 lossless (zero perdita, riduzione moderata)
  - `av1_lossy` — AV1 CRF 30 (ottima compressione, più lento)
  - `av1_lossless` — AV1 lossless (zero perdita)
- **Lavoro incrementale** — un file di stato JSON tiene traccia di tutto. Se il programma si interrompe, riparte da dove si era fermato
- **Verifica integrità** — confronta la durata del video originale e convertito prima di considerare la conversione riuscita
- **Eliminazione originali** — con doppia verifica. Può essere fatto durante la conversione o dopo, su una cartella già convertita
- **Modalità background** — priorità CPU bassa per non disturbare altre applicazioni
- **Statistiche** — tiene traccia dello spazio risparmiato
- **GUI opzionale** — interfaccia grafica con tema chiaro/scuro

## Requisiti

- **FFmpeg** — deve essere installato e nel PATH
  - Windows: [scarica da ffmpeg.org](https://ffmpeg.org/download.html) o `winget install ffmpeg`
  - Debian/Ubuntu: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
- **Python 3.7+** (solo se non usi il binario compilato)

## Installazione

### Binario compilato (consigliato)

Scarica l'eseguibile per il tuo sistema dalla [pagina Releases](https://github.com/BrugnoliDavide/VideoReducer/releases) — non serve Python.

### Da sorgente

```bash
git clone https://github.com/BrugnoliDavide/VideoReducer.git
cd VideoReducer
python -m video_reducer --help
```

## Uso — Riga di comando

### Scansiona una cartella

```bash
video-reducer scan /percorso/cartella/video
video-reducer scan /percorso/cartella/video --size-threshold 200
```

### Mostra i file trovati

```bash
video-reducer list /percorso/cartella/video
video-reducer list /percorso/cartella/video --category heavy_codec
video-reducer list /percorso/cartella/video --status pending
```

### Converti

```bash
# Tutti i file pendenti con preset lossy (default)
video-reducer convert /percorso/cartella/video

# Solo i file con codec pesante, preset quasi-lossless
video-reducer convert /percorso/cartella/video --category heavy_codec --preset lossy_light

# Con eliminazione automatica degli originali
video-reducer convert /percorso/cartella/video --delete-originals

# In background (priorità bassa CPU)
video-reducer convert /percorso/cartella/video --low-priority
```

### Elimina gli originali (post-conversione)

```bash
video-reducer delete-originals /percorso/cartella/video
```

Se nessun file è stato convertito, il programma avvisa e chiede conferma prima di procedere.

### Statistiche

```bash
video-reducer stats /percorso/cartella/video
```

### Preset disponibili

```bash
video-reducer presets
```

## Uso — Interfaccia grafica

```bash
video-reducer gui
```

Oppure doppio click su `video_reducer_gui.bat` (Windows) o `video_reducer_gui.sh` (Linux/macOS).

La GUI offre le stesse funzionalità della CLI con in più:
- Selezione visuale dei file da convertire
- Barra di progresso
- Indicatore di stato chiaro (barra gialla quando lavora)
- Tema chiaro/scuro
- Tutti i bottoni si disabilitano durante le operazioni per evitare doppi avvii

## Esempio reale

Conversione di una clip 4K da una Sony (formato XAVC) con il preset `lossy`:

| | Originale | Convertito |
|---|---|---|
| **Dimensione** | 192.1 MB | 12.6 MB |
| **Codec video** | H.264 High 4:2:2 (XAVC) | H.265 (HEVC) |
| **Risoluzione** | 3840×2160 | 3840×2160 |
| **FPS** | 50 | 50 |
| **Bitrate video** | 200.8 Mbps | 13.6 Mbps |
| **Profondità colore** | 10-bit YUV 4:2:2 | 10-bit YUV 4:2:2 |
| **Audio** | PCM 16-bit (1.5 Mbps) | AAC 128 kbps |
| **Durata** | 7.68s | 7.68s |
| **Riduzione** | — | **-93.4%** |

La risoluzione 4K, i 50fps, la profondità 10-bit e il chroma subsampling 4:2:2 sono tutti preservati.

## Come funziona

1. **Scan** — FFprobe analizza ogni file video nella cartella e raccoglie codec, risoluzione, bitrate, durata
2. **Categorizzazione** — ogni file viene classificato in base al codec e alla dimensione
3. **Conversione** — FFmpeg ricodifica usando il preset scelto. Il file convertito viene salvato nella stessa cartella con suffisso `_reduced`
4. **Verifica** — la durata del file convertito viene confrontata con l'originale (tolleranza 1%)
5. **Stato** — tutto viene salvato in `.video_reducer_state.json` nella cartella. Se il processo si interrompe, al prossimo avvio riparte dai file non ancora convertiti

## Licenza

MIT
