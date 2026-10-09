from fastapi import FastAPI

from backend.db.database import init_db
from backend.api.auth import router as auth_router


app = FastAPI(
    title="AI Meeting Intelligence API"
)


# Initialize database
init_db()

# Authentication routes
app.include_router(auth_router)

@app.get("/")
def root():

    return {
        "message": "AI Meeting Intelligence API is running"
    }