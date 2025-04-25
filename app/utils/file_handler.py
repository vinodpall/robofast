import os
from fastapi import UploadFile
from datetime import datetime
import uuid

async def save_upload_file(upload_file: UploadFile, folder: str = "images") -> str:
    """
    保存上传的文件并返回访问URL
    
    Args:
        upload_file: 上传的文件
        folder: 存储的子文件夹名称
        
    Returns:
        str: 文件的访问URL
    """
    # 生成唯一的文件名
    file_ext = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # 构建存储路径
    current_date = datetime.now().strftime("%Y%m%d")
    save_dir = os.path.join("static", "uploads", folder, current_date)
    os.makedirs(save_dir, exist_ok=True)
    
    # 完整的文件路径
    file_path = os.path.join(save_dir, unique_filename)
    
    # 保存文件
    content = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 返回访问URL
    return f"/static/uploads/{folder}/{current_date}/{unique_filename}" 