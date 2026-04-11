import uvicorn

if __name__ == "__main__":
    print("Starting FinGPT Python API (Core Bridge)...")
    uvicorn.run("python_core.api.main:app", host="127.0.0.1", port=8000, reload=True)
