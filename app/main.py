from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import router
from app.database.database import engine
from app.models import models
import os
import signal
import sys
import asyncio
from app.websockets.video_stream import start_video_stream_server
import threading

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

# 启动WebSocket服务器的函数
def run_websocket_server():
    try:
        asyncio.run(start_video_stream_server())
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger("app.main")
        logger.error(f"WebSocket服务器线程错误: {e}")
        logger.error(f"WebSocket服务器错误详情: {traceback.format_exc()}")
        print(f"WebSocket服务器线程崩溃: {e}")

@app.on_event("startup")
async def startup_event():
    # 在新线程中启动WebSocket服务器
    websocket_thread = threading.Thread(target=run_websocket_server)
    websocket_thread.daemon = True
    websocket_thread.start()

@app.on_event("shutdown")
def shutdown_event():
    # 关闭数据库连接
    engine.dispose()

def signal_handler(sig, frame):
    print("\n正在关闭应用程序...")
    sys.exit(0)

if __name__ == "__main__":
    import uvicorn
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        workers=1
    ) 