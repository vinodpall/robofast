from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy import event
from app.database.database import Base
from datetime import datetime
from typing import List, Optional

# 公司-荣誉关联表
company_award = Table(
    'company_award',
    Base.metadata,
    Column('company_id', Integer, ForeignKey('companies.id'), primary_key=True),
    Column('award_id', Integer, ForeignKey('awards.id'), primary_key=True)
)

class Robot(Base):
    """机器人表"""
    __tablename__ = "robots"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))  # 机器人名称
    industry_type = Column(String(50))  # 种类-工业机器人
    company_id = Column(Integer, ForeignKey("companies.id"))  # 品牌-外键关联公司表
    price = Column(Float)  # 单价-10000
    serial_number = Column(String(50))  # 编号-89757
    create_date = Column(String(50))  # 创建日期-202503201900
    status = Column(String(20))  # 状态：在线/离线/故障
    skills = Column(String(200))  # 技能特点
    product_location = Column(String(100))  # 产地
    dimensions = Column(String(100))  # 参考重量尺寸
    image_url = Column(String(255))  # 图片地址
    remarks = Column(Text)  # 备注说明
    training_field_id = Column(Integer, ForeignKey("training_fields.id"))  # 训练场-外键关联训练场表
    awards = Column(String(500))  # 荣誉-字符串形式
    recommendation_reason = Column(String(500))  # 推荐理由
    is_carousel = Column(Boolean, default=False)  # 是否轮播
    carousel_add_time = Column(String(50))  # 加入轮播时间-202504031214
    
    # 关系
    company = relationship("Company", back_populates="robots")
    training_field = relationship("TrainingField", back_populates="robots")
    data_records = relationship("DataRecord", back_populates="robot", lazy="selectin")

# 添加事件监听器
@event.listens_for(Robot, 'before_update')
def set_carousel_add_time(mapper, connection, target):
    if target.is_carousel and not target.carousel_add_time:
        target.carousel_add_time = str(int(datetime.now().timestamp()))

class TrainingField(Base):
    """训练场表"""
    __tablename__ = "training_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 训练场名称
    description = Column(Text)  # 训练场简介
    image_url = Column(String(255))  # 场景图片URL

    # 关系
    robots = relationship("Robot", back_populates="training_field")

class Company(Base):
    """公司表"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 公司名称
    description = Column(Text)  # 简介
    is_carousel = Column(Boolean, default=False)  # 是否轮播
    create_time = Column(String(50))  # 创建时间-202504031600
    
    # 关系
    awards = relationship("Award", secondary=company_award, back_populates="companies")
    robots = relationship("Robot", back_populates="company")

class Award(Base):
    """荣誉证书表"""
    __tablename__ = "awards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 荣誉名称
    description = Column(Text)  # 荣誉简介
    image_url = Column(String(255))  # 图片URL
    is_carousel = Column(Boolean, default=False)  # 是否轮播

    # 关系
    companies = relationship("Company", secondary=company_award, back_populates="awards")

class Video(Base):
    """视频表"""
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 视频名称
    description = Column(Text)  # 视频简介
    url = Column(String(255))  # 视频URL
    type = Column(String(20))  # 视频类型
    is_carousel = Column(Boolean, default=False)  # 是否轮播
    carousel_add_time = Column(String(50))  # 加入轮播时间
    create_time = Column(String(50))  # 创建时间-时间戳字符串

class VisitorRecord(Base):
    """参观记录表"""
    __tablename__ = "visitor_records"
    
    id = Column(Integer, primary_key=True, index=True)
    visitor_count = Column(Integer, default=0)  # 参观人数
    visit_date = Column(String(50))  # 时间-20250420

class DataType(Base):
    """数据类型表"""
    __tablename__ = "data_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # 数据类型名称

class DataRecord(Base):
    """数据采集记录表"""
    __tablename__ = "data_records"
    
    id = Column(Integer, primary_key=True, index=True)
    data_type_id = Column(Integer, ForeignKey("data_types.id"))  # 数据类型-外键关联数据类型表
    collect_date = Column(String(50))  # 时间-20250402
    robot_id = Column(Integer, ForeignKey("robots.id"))  # 机器人-外键关联机器人表
    count = Column(Integer)  # 数量
    
    # 关系
    data_type = relationship("DataType", backref="records")
    robot = relationship("Robot", back_populates="data_records", lazy="selectin")

class WebConfig(Base):
    """网页配置信息表"""
    __tablename__ = "web_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="网页名称")
    icon_url = Column(String(255), nullable=True, comment="图标URL")
    video_carousel = Column(Boolean, default=False, comment="视频是否轮播")
    page_carousel = Column(Boolean, default=False, comment="网页是否轮播")
    current_carousel_page = Column(Integer, nullable=True, comment="当前轮播页")
    first_page_duration = Column(Integer, nullable=True, comment="第一页停留时间(秒)")
    second_page_duration = Column(Integer, nullable=True, comment="第二页停留时间(秒)")
    third_page_duration = Column(Integer, nullable=True, comment="第三页停留时间(秒)")
    visitor_count = Column(Integer, nullable=True, comment="来访人数统计")
    weekly_visitor_count = Column(Integer, nullable=True, comment="本周访客数")
    monthly_visitor_count = Column(Integer, nullable=True, comment="本月访客数")
    video_carousel_duration = Column(Integer, nullable=True, comment="视频轮播停留时间(秒)") 