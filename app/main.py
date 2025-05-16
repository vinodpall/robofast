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
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# 全局变量存储WebSocket服务器线程
websocket_thread = None

# 启动WebSocket服务器的函数
def run_websocket_server():
    try:
        logger.info("正在启动WebSocket服务器...")
        asyncio.run(start_video_stream_server())
    except Exception as e:
        logger.error(f"WebSocket服务器线程错误: {e}")
        import traceback
        logger.error(f"WebSocket服务器错误详情: {traceback.format_exc()}")
        print(f"WebSocket服务器线程崩溃: {e}")

# 手动启动WebSocket服务器的函数
def start_websocket():
    global websocket_thread
    if websocket_thread is None or not websocket_thread.is_alive():
        websocket_thread = threading.Thread(target=run_websocket_server)
        websocket_thread.daemon = True
        websocket_thread.start()
        logger.info("WebSocket服务器线程已启动")
    else:
        logger.info("WebSocket服务器已经在运行中")

# 自动启动WebSocket服务器的代码（已注释）
# @app.on_event("startup")
# async def startup_event():
#     global websocket_thread
#     # 在新线程中启动WebSocket服务器
#     websocket_thread = threading.Thread(target=run_websocket_server)
#     websocket_thread.daemon = True
#     websocket_thread.start()
#     logger.info("WebSocket服务器线程已启动")

@app.on_event("shutdown")
def shutdown_event():
    # 关闭数据库连接
    engine.dispose()
    logger.info("数据库连接已关闭")

def signal_handler(signum, frame):
    logger.info(f"收到信号 {signum}，正在关闭应用...")
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