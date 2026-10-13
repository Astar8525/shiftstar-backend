from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from database import engine
import models
from routers import users, shifts, events, production, history, stripe_routes, ai_routes, reset_routes, admin_routes

models.Base.metadata.create_all(bind=engine)
from sqlalchemy import inspect as _inspect, text as _text
if 'invite_code' not in [c['name'] for c in _inspect(engine).get_columns('companies')]:
    with engine.begin() as _conn:
        _conn.execute(_text('ALTER TABLE companies ADD COLUMN invite_code VARCHAR'))

app = FastAPI(
    title="ShiftStar API",
    description="Manufacturing shift intelligence platform — Built for the floor. Understood in the boardroom.",
    version="1.1.0"
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
app.include_router(ai_routes.router)
app.include_router(reset_routes.router)
app.include_router(admin_routes.router)

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("dashboard.html")

@app.get("/")
def serve_landing():
    return FileResponse("index.html")

@app.get("/privacy")
def serve_privacy():
    return FileResponse("privacy.html")

@app.get("/terms")
def serve_terms():
    return FileResponse("terms.html")

@app.get("/ethics")
def serve_ethics():
    return FileResponse("ethics.html")

@app.get("/admin")
def serve_admin():
    return FileResponse("admin.html")

@app.get("/import-guide")
def serve_import_guide():
    return FileResponse("import-guide.html")

@app.get("/samples/{filename}")
def serve_sample(filename: str):
    allowed = [
        "ShiftStar_Sample_CSV_24hr.csv",
        "ShiftStar_Sample_CSV_7day.csv",
        "ShiftStar_Sample_CSV_30day.csv",
        "ShiftStar_Sample_SAP_24hr.csv",
        "ShiftStar_Sample_SAP_7day.csv",
        "ShiftStar_Sample_SAP_30day.csv",
        "ShiftStar_Sample_MRP_24hr.csv",
        "ShiftStar_Sample_MRP_7day.csv",
        "ShiftStar_Sample_MRP_30day.csv",
    ]
    if filename not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(f"samples/{filename}", filename=filename, media_type="text/csv")

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.1.0"}
