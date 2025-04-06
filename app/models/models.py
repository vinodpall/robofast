from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database.database import Base
from datetime import datetime

class Robot(Base):
    """机器人表"""
    __tablename__ = "robots"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # 机器人名称
    robot_type = Column(String(50), nullable=False)  # 机器人类型-第一代
    industry_type = Column(String(50), nullable=False)  # 种类-工业机器人
    product_series = Column(String(50))  # 品牌-外骨
    price = Column(Float)  # 单价-10000
    serial_number = Column(String(50), unique=True)  # 编号-89757
    create_date = Column(String(50))  # 创建日期-202503201900
    status = Column(String(20))  # 状态：在线/离线/故障
    training_status = Column(String(50))  # 训练状态：上线/培训中/上市中
    skills = Column(Text)  # 技能特点
    awards = Column(Text)  # 获得的荣誉
    product_location = Column(String(100))  # 产地
    dimensions = Column(String(100))  # 参考重量尺寸
    image_url = Column(String(255))  # 图片地址
    remarks = Column(Text)  # 备注说明
    is_active = Column(Boolean, default=True)  # 是否在用

class TrainingField(Base):
    """训练场表"""
    __tablename__ = "training_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 训练场名称
    description = Column(Text)  # 训练场说明
    image_url = Column(String(255))  # 图片地址
    create_time = Column(DateTime, default=datetime.now)

class Company(Base):
    """公司表"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 公司名称
    description = Column(Text)  # 简介
    address = Column(String(255))  # 地址
    contact = Column(String(50))  # 联系方式
    create_time = Column(DateTime, default=datetime.now)
    expiry_time = Column(DateTime)  # 到期时间-202504031600

class Award(Base):
    """荣誉证书表"""
    __tablename__ = "awards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 荣誉名称
    description = Column(Text)  # 荣誉说明
    issue_date = Column(DateTime)  # 颁发日期
    image_url = Column(String(255))  # 证书图片地址
    create_time = Column(DateTime, default=datetime.now)

class Video(Base):
    """视频表"""
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))  # 视频标题
    url = Column(String(255), nullable=False)  # 视频地址
    type = Column(String(20))  # 类型：在线流/本地视频
    description = Column(Text)  # 视频描述
    create_time = Column(DateTime, default=datetime.now)

class VisitorRecord(Base):
    """参观记录表"""
    __tablename__ = "visitor_records"
    
    id = Column(Integer, primary_key=True, index=True)
    visit_date = Column(DateTime, nullable=False)  # 参观日期
    visitor_count = Column(Integer, default=0)  # 参观人数
    create_time = Column(DateTime, default=datetime.now)

class DataType(Base):
    """数据类型表"""
    __tablename__ = "data_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # 数据类型名称
    description = Column(Text)  # 类型说明
    unit = Column(String(20))  # 单位
    create_time = Column(DateTime, default=datetime.now)

class DataRecord(Base):
    """数据采集记录表"""
    __tablename__ = "data_records"
    
    id = Column(Integer, primary_key=True, index=True)
    data_type_id = Column(Integer, ForeignKey("data_types.id"))  # 数据类型ID
    value = Column(String(255))  # 采集的数据值
    collect_time = Column(DateTime)  # 采集时间
    create_time = Column(DateTime, default=datetime.now)
    
    data_type = relationship("DataType", backref="records")

class WebConfig(Base):
    """网页配置信息表"""
    __tablename__ = "web_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)  # 配置键
    value = Column(Text)  # 配置值
    description = Column(Text)  # 配置说明
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, onupdate=datetime.now) 