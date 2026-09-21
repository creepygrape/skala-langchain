from fastapi import FastAPI

from app.api import ticket_guide_router


app = FastAPI(title="Concert Ticket Guide API")
app.include_router(ticket_guide_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return the backend health status."""
    return {"status": "ok"}
