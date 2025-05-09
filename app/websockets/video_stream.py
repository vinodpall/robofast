import asyncio
import websockets
import json
from typing import Dict, Set
import logging
import subprocess
import urllib.parse
import select
import time
import sys

# 设置日志 - 改为 ERROR 级别，只显示错误
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# 存储活跃的WebSocket连接
active_connections: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}

# 存储已永久关闭的URL
permanently_closed_urls: Set[str] = set()

async def handle_test_connection(websocket: websockets.WebSocketServerProtocol):
    """处理测试连接"""
    try:
        await websocket.send(json.dumps({"status": "connected", "message": "WebSocket server is running"}))
        await websocket.close(1000, "Test completed")
    except Exception as e:
        logger.error(f"测试连接处理错误: {str(e)}")

async def handle_video_stream(websocket: websockets.WebSocketServerProtocol):
    """处理视频流WebSocket连接"""
    video_url = None
    process = None
    retry_count = 0
    max_retries = 2
    
    try:
        # 从websocket的request中获取RTSP URL
        if not hasattr(websocket, 'request'):
            logger.error("WebSocket对象没有request属性")
            await websocket.close(1008, "Invalid WebSocket connection")
            return
            
        # 获取请求路径
        request_path = websocket.request.path
        
        video_url = request_path.lstrip('/')
        if not video_url:
            logger.error("URL为空")
            await websocket.close(1008, "Missing RTSP URL")
            return

        # 解码URL
        video_url = urllib.parse.unquote(video_url)
        if not video_url:
            logger.error("解码后的URL为空")
            await websocket.close(1008, "Invalid RTSP URL")
            return

        # 检查URL是否已永久关闭
        if video_url in permanently_closed_urls:
            logger.warning(f"URL {video_url} 已永久关闭，拒绝连接")
            await websocket.close(1011, "Connection permanently closed")
            return

        # 将连接添加到活跃连接集合中
        if video_url not in active_connections:
            active_connections[video_url] = set()
        active_connections[video_url].add(websocket)
        
        # 获取当前事件循环
        loop = asyncio.get_running_loop()
        
        # 定义启动FFmpeg进程的函数
        async def start_ffmpeg_process():
            nonlocal process, retry_count
            
            # 构建FFmpeg命令 - 使用MJPEG格式
            command = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-timeout', '5',     # 设置5秒超时
                '-i', video_url,
                '-f', 'mjpeg',       # MJPEG格式替代rawvideo
                '-q:v', '5',         # JPEG质量 (1-31，1最好但文件最大)
                '-s', '674x384',     # 降低分辨率
                '-r', '20',          # 限制帧率为20fps
                '-loglevel', 'error', # 只显示错误信息
                'pipe:1'
            ]
            
            # 使用subprocess直接运行FFmpeg命令
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            
            # 检查FFmpeg是否成功启动
            if process.poll() is not None:
                stderr_data = process.stderr.read()
                if stderr_data:
                    logger.error(f"FFmpeg启动失败: {stderr_data.decode('utf-8', errors='ignore')}")
                retry_count += 1
                if retry_count >= max_retries:
                    permanently_closed_urls.add(video_url)
                    raise Exception("FFmpeg进程启动失败，已达到最大重试次数")
                raise Exception("FFmpeg进程启动失败")
            
            return process

        try:
            # 启动FFmpeg进程
            process = await start_ffmpeg_process()
            
            # 启动一个任务来读取FFmpeg的错误输出
            async def read_stderr():
                while True:
                    try:
                        # 在线程池中执行阻塞读取
                        line = await loop.run_in_executor(None, process.stderr.readline)
                        if not line:
                            break
                        # 只记录错误信息
                        stderr_line = line.decode('utf-8', errors='ignore').strip()
                        if stderr_line and ('error' in stderr_line.lower() or 'fail' in stderr_line.lower()):
                            logger.error(f"FFmpeg错误: {stderr_line}")
                    except Exception as e:
                        logger.error(f"读取FFmpeg stderr时出错: {e}")
                        break
            
            # 启动错误输出读取任务
            stderr_task = asyncio.create_task(read_stderr())
            
            # 等待1秒，让FFmpeg有更多时间建立连接
            await asyncio.sleep(1)
            
            # 检查进程是否还在运行
            if process.poll() is not None:
                logger.warning("FFmpeg进程启动后立即退出")
                retry_count += 1
                if retry_count >= max_retries:
                    permanently_closed_urls.add(video_url)
                    await websocket.close(1011, "Failed to start FFmpeg process, maximum retries reached")
                    return
                raise Exception("FFmpeg进程启动失败")
            
            # MJPEG格式处理
            frame_count = 0
            last_log_time = time.time()
            no_data_count = 0  # 计数器，用于检测长时间无数据
            jpeg_start_marker = b'\xff\xd8'  # JPEG文件的起始标记
            jpeg_end_marker = b'\xff\xd9'    # JPEG文件的结束标记
            buffer = bytearray()
            
            while True:
                try:
                    # 检查进程是否还在运行
                    poll_result = process.poll()
                    if poll_result is not None:
                        stderr_data = await loop.run_in_executor(None, process.stderr.read)
                        if stderr_data:
                            logger.error(f"FFmpeg错误输出: {stderr_data.decode('utf-8', errors='ignore')}")
                        logger.warning(f"FFmpeg进程已退出，返回码: {poll_result}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            permanently_closed_urls.add(video_url)
                            await websocket.close(1011, "FFmpeg process exited, maximum retries reached")
                            return
                        raise Exception("FFmpeg进程退出")
                    
                    # 在线程池中执行阻塞读取
                    chunk = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: process.stdout.read(32768)),
                        timeout=1.0  # 设置1秒超时
                    )
                    
                    if not chunk:
                        no_data_count += 1
                        if no_data_count > 10:  # 减少无数据等待次数
                            logger.warning("长时间没有读取到数据，可能连接已断开")
                            retry_count += 1
                            if retry_count >= max_retries:
                                permanently_closed_urls.add(video_url)
                                await websocket.close(1011, "No data received, maximum retries reached")
                                return
                            raise Exception("No data received")
                        await asyncio.sleep(0.1)  # 短暂等待后重试
                        continue
                    
                    no_data_count = 0  # 重置计数器
                    current_time = time.time()
                    
                    # 添加到缓冲区
                    buffer.extend(chunk)
                    
                    # 查找并处理完整的JPEG帧
                    while True:
                        # 查找JPEG起始标记
                        start_idx = buffer.find(jpeg_start_marker)
                        if start_idx == -1:
                            # 没有找到起始标记，清空无用数据
                            buffer.clear()
                            break
                        elif start_idx > 0:
                            # 丢弃起始标记之前的数据
                            buffer = buffer[start_idx:]
                        
                        # 查找JPEG结束标记
                        end_idx = buffer.find(jpeg_end_marker, 2)  # 跳过起始标记后查找
                        if end_idx == -1:
                            # 没有找到结束标记，等待更多数据
                            break
                        
                        # 提取完整的JPEG帧 (包括结束标记)
                        end_idx += 2  # 包含结束标记的长度
                        frame_data = bytes(buffer[:end_idx])
                        buffer = buffer[end_idx:]  # 移除已处理的帧数据
                        
                        # 计数并记录
                        frame_count += 1
                        
                        # 发送帧数据
                        try:
                            await websocket.send(frame_data)
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("客户端连接已关闭")
                            if not stderr_task.done():
                                stderr_task.cancel()
                            return
                        except Exception as e:
                            logger.error(f"发送视频帧时出错: {str(e)}")
                            continue
                
                except asyncio.TimeoutError:
                    # 读取超时，继续尝试
                    continue
                except Exception as e:
                    logger.error(f"读取视频帧时出错: {str(e)}")
                    import traceback
                    logger.error(f"详细错误信息: {traceback.format_exc()}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        permanently_closed_urls.add(video_url)
                        await websocket.close(1011, "Error reading video frames, maximum retries reached")
                        return
                    raise
            
        except Exception as e:
            logger.error(f"FFmpeg处理错误: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            retry_count += 1
            if retry_count >= max_retries:
                permanently_closed_urls.add(video_url)
                await websocket.close(1011, "FFmpeg processing error, maximum retries reached")
                return
            # 如果未达到最大重试次数，重新启动FFmpeg进程
            try:
                process = await start_ffmpeg_process()
            except Exception as retry_error:
                logger.error(f"重试FFmpeg进程失败: {str(retry_error)}")
                permanently_closed_urls.add(video_url)
                await websocket.close(1011, "Failed to retry FFmpeg process")
                return
            return
        finally:
            # 清理stderr_task
            if 'stderr_task' in locals() and not stderr_task.done():
                stderr_task.cancel()
                try:
                    await stderr_task
                except asyncio.CancelledError:
                    pass
            
            # 终止FFmpeg进程
            if process and process.poll() is None:
                try:
                    process.terminate()
                    await loop.run_in_executor(None, process.wait)
                except Exception as e:
                    logger.error(f"终止 FFmpeg 进程时出错: {str(e)}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.warning(f"客户端断开连接: {video_url}")
    except Exception as e:
        logger.error(f"处理视频流时出错: {str(e)}")
        # 打印完整的错误堆栈
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
    finally:
        # 清理连接
        if video_url and video_url in active_connections:
            if websocket in active_connections[video_url]:
                active_connections[video_url].remove(websocket)
            if not active_connections[video_url]:
                del active_connections[video_url]

async def start_video_stream_server():
    """启动视频流WebSocket服务器"""
    try:
        # 启动测试服务器
        test_server = await websockets.serve(
            handle_test_connection,
            "0.0.0.0",
            8766
        )

        # 启动视频流服务器
        async with websockets.serve(
            handle_video_stream,
            "0.0.0.0",
            8765,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10,
            max_size=None  # 允许发送任意大小的消息
        ) as server:
            await asyncio.gather(
                test_server.wait_closed(),
                server.wait_closed()
            )
    except Exception as e:
        logger.error(f"启动WebSocket服务器时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise 