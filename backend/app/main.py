"""Точка входа FastAPI-приложения."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import campaigns, offers, streams

app = FastAPI(
    title="Keitaro Campaign Manager",
    description="Тестовое задание Adrobot: создание кампаний и редактор офферов",
    version="1.0.0",
)

# CORS открыт для dev-режима (Vite крутится на :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router)
app.include_router(offers.router)
app.include_router(streams.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
