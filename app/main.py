from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, employees, ingestion, review, search

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SkillsHub API", version="1.0.0", description="AI-Powered Skills Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(ingestion.router)
app.include_router(review.router)
app.include_router(search.router)


@app.get("/")
def root():
    return {"message": "SkillsHub API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
