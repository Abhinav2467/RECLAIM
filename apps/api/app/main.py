from fastapi import FastAPI
from app.api.webhooks import router as webhooks_router
from app.api.recovery_cases import router as recovery_cases_router
from app.api.demo import router as demo_router
from app.api.auth import router as auth_router

app = FastAPI(
    title="RECLAIM API",
    version="0.1.0",
    description="Revenue Recovery Decision Engine",
)

# Register routes
app.include_router(webhooks_router, prefix="/webhooks/providers")
app.include_router(recovery_cases_router, prefix="/api")
app.include_router(demo_router, prefix="/api")
app.include_router(auth_router, prefix="/api")



@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
