from fastapi import FastAPI


app = FastAPI(title="Concert Ticket Guide API")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return the backend health status."""
    return {"status": "ok"}
