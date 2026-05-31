from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from routers import users, shifts, events, production, history

# Create all database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ShiftStar API",
    description="Manufacturing shift intelligence platform — Built for the floor. Understood in the boardroom.",
    version="1.0.0"
)

# Allow the dashboard to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(users.router)
app.include_router(shifts.router)
app.include_router(events.router)
app.include_router(production.router)
app.include_router(history.router)

@app.get("/")
def root():
    return {
        "product": "ShiftStar",
        "version": "1.0.0",
        "tagline": "Built for the floor. Understood in the boardroom.",
        "status": "running",
        "docs": "/docs"
    }

from fastapi.responses import FileResponse

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("dashboard.html")

@app.get("/health")
def health():
    return {"status": "healthy"}

