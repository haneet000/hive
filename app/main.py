from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine, Base
from app.routes import revenue, customers, stats, ingestion

app = FastAPI(
    title="Hive E-Commerce Analytics API",
    description="Production-grade API for third-party e-commerce feed ingestion, data validation, and business analytics.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(revenue.router)
app.include_router(customers.router)
app.include_router(stats.router)
app.include_router(ingestion.router)

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "service": "Hive E-Commerce Analytics API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }
