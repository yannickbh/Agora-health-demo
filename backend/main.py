from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers import agent, system

app = FastAPI(title="Hospital Support Agent — Powered by Agora ConvoAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router, tags=["Agent"])
app.include_router(system.router, tags=["System"])

# Mount frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("frontend/index.html")
