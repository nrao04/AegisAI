from fastapi import FastAPI

app = FastAPI()

@app.get("/")

def read_root():
    return {"message": "Welcome to AegisAI – AI-Powered Incident Response System"}

