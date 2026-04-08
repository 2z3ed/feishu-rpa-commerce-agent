from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.config import config
from src.models import db

# Create FastAPI application
app = FastAPI(
    title="Feishu RPA Commerce Agent",
    description="A Feishu-driven commerce backoffice agent with RPA-first execution",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    await db.init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application on shutdown"""
    await db.close_db()


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Feishu RPA Commerce Agent API", "version": "0.1.0"}


@app.post("/webhook/feishu")
async def feishu_webhook(request: Request):
    """Feishu webhook endpoint"""
    try:
        data = await request.json()
        # TODO: Implement webhook handling logic
        return {"success": True, "message": "Webhook received"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}