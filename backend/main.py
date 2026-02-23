from fastapi import FastAPI

app = FastAPI()

# root endpoint for testing and health checks
@app.get("/")

def read_root():
    return {"message": "Welcome to AegisAI – AI-Powered Incident Response System"}

# if script is run directly, launch FastAPI app using uvicorn
if __name__ == "__main__":
    import uvicorn
    # run app on localhost at port 8000 with auto-reloading enabled
    # use import string "main:app" so uvicorn can reload on file changes
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)