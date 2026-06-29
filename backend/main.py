import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from fastapi import FastAPI  # type: ignore[import-not-found]
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "Backend dependencies are missing. Install them with: "
        "C:/Users/HP/Desktop/tata/backend/venv2/Scripts/python.exe -m pip install -r requirements.txt"
    ) from exc

from app.api.routes import router
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CineMatch AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Welcome to CineMatch AI API"}


if __name__ == "__main__":
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Uvicorn is missing. Install backend dependencies first."
        ) from exc

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
