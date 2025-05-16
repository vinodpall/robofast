import requests
import logging
import sys
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.crud import crud_video
from app.schemas import video as video_schema
from app.api import deps
from app.models.video import Video
from sqlalchemy import desc

# 配置日志
logger = logging.getLogger("video_api")
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(console_handler)

router = APIRouter()

def get_mediamtx_streams() -> List[str]:
    """获取 mediamtx 当前所有的流名称"""
    try:
        print("\n正在获取 mediamtx 流列表...")
        response = requests.get(
            "http://localhost:9997/v3/paths/list",
            auth=("apiadmin", "apipassword123")
        )
        print(f"获取流列表响应状态码: {response.status_code}")
        print(f"获取流列表响应内容: {response.text}")
        response.raise_for_status()
        data = response.json()
        streams = [item["name"] for item in data.get("items", [])]
        print(f"当前流列表: {streams}")
        return streams
    except Exception as e:
        print(f"获取 mediamtx 流失败: {str(e)}")
        if hasattr(e, 'response'):
            print(f"错误响应状态码: {e.response.status_code}")
            print(f"错误响应内容: {e.response.text}")
        return []

def add_mediamtx_stream(name: str, url: str):
    """添加新的流到 mediamtx"""
    try:
        print(f"\n正在添加流: name={name}, url={url}")
        # 使用 /v3/config/paths/add/{name} 接口添加流
        response = requests.post(
            f"http://localhost:9997/v3/config/paths/add/{name}",
            auth=("apiadmin", "apipassword123"),
            json={
                "source": url,
                "sourceOnDemand": True,
                "rtspTransport": "tcp",
                "runOnDemand": True,
                "runOnDemandStartTimeout": "10s",
                "runOnDemandCloseAfter": "10s"
            }
        )
        print(f"添加流响应状态码: {response.status_code}")
        print(f"添加流响应内容: {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"添加 mediamtx 流失败: {str(e)}")
        if hasattr(e, 'response'):
            print(f"错误响应状态码: {e.response.status_code}")
            print(f"错误响应内容: {e.response.text}")

def remove_mediamtx_stream(name: str):
    """从 mediamtx 中移除流"""
    try:
        print(f"\n正在移除流: name={name}")
        # 使用 /v3/config/paths/delete/{name} 接口删除流
        response = requests.delete(
            f"http://localhost:9997/v3/config/paths/delete/{name}",
            auth=("apiadmin", "apipassword123")
        )
        print(f"移除流响应状态码: {response.status_code}")
        print(f"移除流响应内容: {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"移除 mediamtx 流失败: {str(e)}")
        if hasattr(e, 'response'):
            print(f"错误响应状态码: {e.response.status_code}")
            print(f"错误响应内容: {e.response.text}")

@router.get("/carousel", response_model=List[video_schema.Video])
def get_carousel_videos(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100
) -> List[Video]:
    """
    获取轮播视频列表，优先显示 is_carousel 为 true 的视频，并按创建时间降序排序
    """
    print("\n=== 开始处理轮播视频 ===")
    
    # 获取所有轮播视频
    videos = crud_video.get_carousel_videos(db, skip=skip, limit=limit)
    print(f"\n获取到的轮播视频数量: {len(videos)}")
    for video in videos:
        print(f"视频详细信息:")
        print(f"  ID: {video.id}")
        print(f"  名称: {video.name}")
        print(f"  类型: {video.type}")
        print(f"  英文名: {video.en_name}")
        print(f"  URL: {video.url}")
        print(f"  是否轮播: {video.is_carousel}")
        print(f"  创建时间: {video.create_time}")
        print("  ---")
    
    # 获取当前 mediamtx 中的流
    current_streams = get_mediamtx_streams()
    print(f"\n当前 mediamtx 流数量: {len(current_streams)}")
    print(f"当前 mediamtx 流列表: {current_streams}")
    
    # 获取所有 RTSP 类型的视频
    rtsp_videos = [video for video in videos if video.type == "rtsp"]
    rtsp_names = {video.en_name for video in rtsp_videos}
    print(f"\nRTSP 视频数量: {len(rtsp_videos)}")
    print(f"RTSP 视频名称: {rtsp_names}")
    
    # 添加新的流
    for video in rtsp_videos:
        if video.en_name not in current_streams:
            print(f"\n需要添加新流: {video.en_name}")
            print(f"流地址: {video.url}")
            add_mediamtx_stream(video.en_name, video.url)
    
    # 删除不再需要的流（排除默认配置的流）
    default_streams = {"camera_1", "camera_2"}  # 默认配置的流名称
    for stream_name in current_streams:
        if stream_name not in rtsp_names and stream_name not in default_streams:
            print(f"\n需要删除流: {stream_name}")
            remove_mediamtx_stream(stream_name)
    
    print("\n=== 轮播视频处理完成 ===\n")
    return videos 