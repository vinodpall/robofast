from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import router
from app.database.database import engine
from app.models import models
import os

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

# 配置静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 包含路由
app.include_router(router, prefix="/api")

@app.on_event("shutdown")
async def shutdown_event():
    # 关闭数据库连接
    await engine.dispose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 