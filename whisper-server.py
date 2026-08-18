"""
Whisper Server BABOO — trascrizione conversazioni di sopralluogo
================================================================
Micro-servizio FastAPI + faster-whisper per l'app Sopralluoghi BABOO.
L'audio del cliente resta nel perimetro BABOO (Energy Brain): nessun dato a terzi.

INSTALLAZIONE (Energy Brain, Ubuntu 24.04) — da eseguire quando decidi tu:
--------------------------------------------------------------------------
  mkdir -p /opt/whisper-baboo && cd /opt/whisper-baboo
  python3 -m venv venv && source venv/bin/activate
  pip install fastapi uvicorn python-multipart faster-whisper
  # copia questo file come /opt/whisper-baboo/whisper-server.py
  # primo avvio: scarica il modello 'small' (~460 MB), poi resta in cache

  # prova manuale:
  uvicorn whisper-server:app --host 127.0.0.1 --port 8091

  # in produzione con pm2 (già presente sul VPS):
  pm2 start "venv/bin/uvicorn whisper-server:app --host 127.0.0.1 --port 8091" \
      --name whisper-baboo --cwd /opt/whisper-baboo
  pm2 save

NGINX (energybrain.baboo.eu) — aggiungere nel server block HTTPS:
-----------------------------------------------------------------
  location /whisper/ {
      client_max_body_size 60m;              # audio fino a ~30 min
      proxy_read_timeout 300s;               # trascrizione CPU: tempo
      proxy_pass http://127.0.0.1:8091/;
  }

Poi in app (Strumenti): Server BABOO + URL
  https://energybrain.baboo.eu/whisper/transcribe

NOTE:
- Modello 'small' int8 su CPU: ~1-2 min di elaborazione per 10 min di audio,
  qualità ottima per l'italiano parlato. Per più velocità: 'base'; per più
  qualità: 'medium' (RAM ~3 GB).
- Endpoint volutamente aperto in CORS verso la pagina GitHub Pages; se vuoi
  restringerlo, imposta ALLOWED_ORIGIN qui sotto.
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import tempfile, os

ALLOWED_ORIGIN = "*"   # es. "https://renato-clementi.github.io"
MODEL_SIZE = "small"   # base | small | medium

app = FastAPI(title="Whisper BABOO")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN] if ALLOWED_ORIGIN != "*" else ["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Caricato una volta all'avvio, riusato per ogni richiesta
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "conv.m4a")[1] or ".m4a"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        segments, info = model.transcribe(
            path, language="it", vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return {"text": text, "duration": round(info.duration, 1)}
    finally:
        os.unlink(path)


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_SIZE}
