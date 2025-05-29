from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import base
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Multi-Agents API",
    description="API for Multi-Agents project",
    version="0.1.0"
)

# CORS 设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(base.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Multi-Agents API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 