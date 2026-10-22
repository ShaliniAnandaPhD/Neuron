# FFSapp: Fantasy Football Neuron web app

A single-page fantasy football assistant (`frontend/index.html`, served by
nginx) with a small Flask backend that narrates the assistant's messages.

## Run it

```bash
cd FFSapp
docker compose up --build
# frontend: http://localhost   backend: http://localhost:5000
```

Or without Docker:

```bash
pip install -r FFSapp/backend/requirements.txt
python FFSapp/backend/app.py          # backend on http://127.0.0.1:5000
open FFSapp/frontend/index.html       # or serve the folder with any web server
```

## Backend API

| Endpoint | Request | Response |
|----------|---------|----------|
| `POST /api/narrate` | `{"text": "..."}` | `audio/mpeg` narration |
| `GET /api/health` | | `{"status": "ok"}` |

Narration is a mock: `MockAudioGen` returns a short silent MP3 so the
frontend's audio playback works without speech API credentials. To produce
real speech, replace `MockAudioGen.generate_audio_overview` with a call to a
text to speech service.

The NFL data pipeline that feeds the live product is in
[`../FS_Neuron`](../FS_Neuron).
