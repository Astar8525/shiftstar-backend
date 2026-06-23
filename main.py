from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from database import engine
import models
from routers import users, shifts, events, production, history, stripe_routes

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ShiftStar API",
    description="Manufacturing shift intelligence platform — Built for the floor. Understood in the boardroom.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(shifts.router)
app.include_router(events.router)
app.include_router(production.router)
app.include_router(history.router)
app.include_router(stripe_routes.router)

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("dashboard.html")

@app.get("/")
def serve_landing():
    return FileResponse("index.html")

@app.get("/privacy")
def serve_privacy():
    return FileResponse("privacy.html")

@app.get("/health")
def health():
    return {"status": "healthy"}