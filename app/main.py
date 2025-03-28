from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.database.database import engine
from app.models import models

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RoboFast API",
    description="机器人训练场数据展示系统API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(router, prefix="/api") 