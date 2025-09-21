#!/usr/bin/env python3

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="MOD UI Service", version="0.1.0")

HTML_DIR = os.environ.get('MOD_HTML_DIR', os.path.join(os.path.dirname(__file__), '..', '..', 'html'))

app.mount("/", StaticFiles(directory=HTML_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)