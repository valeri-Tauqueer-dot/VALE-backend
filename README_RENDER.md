# VALE — Render deployment

## Files
- main.py
- index.html
- database.py
- auth.py
- ai_core.py
- requirements.txt
- render.yaml

## Render
Build command: `pip install -r requirements.txt`
Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Environment variables
- `DATABASE_URL`: your Supabase/PostgreSQL connection string
- `SECRET_KEY`: a strong secret; the Blueprint can generate it automatically

The FastAPI service serves `index.html` at `/`. The frontend uses the same origin for `/login`, `/profile`, `/chat`, `/health`, and `/signup`.
