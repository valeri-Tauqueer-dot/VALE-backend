from fastapi import FastAPI
from pydantic import BaseModel

from ai_core import vale

app = FastAPI(
    title="VALE AI Core",
    version="1.0"
)


class UserMessage(BaseModel):
    message: str


@app.get("/")
def home():
    return {
        "system": "VALE AI",
        "status": "Online",
        "version": "1.0"
    }


@app.post("/chat")
def chat(data: UserMessage):

    response = vale.process(data.message)

    return {
        "user": data.message,
        "vale": response
    }