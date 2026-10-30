
from fastapi import FastAPI

from backend.db.database import init_db
from backend.api.auth import router as auth_router
from backend.api.meetings import router as meetings_router

app = FastAPI(title="AI Meeting Intelligence API")

init_db()

app.include_router(auth_router)
app.include_router(meetings_router)


@app.get("/")
def root():
    return {"message": "AI Meeting Intelligence API is running"}
