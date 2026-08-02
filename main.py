from fastapi import FastAPI

app = FastAPI(
    title="VALE Backend",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Welcome to VALE Backend"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
