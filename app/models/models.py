from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.database.database import Base

class Robot(Base):
    """机器人信息表"""
    __tablename__ = "robots"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    name = Column(String(50))  # 机器人名称
    parameters = Column(String(50))  # 参数配置
    body_type = Column(String(50))  # 机器人体型类别
    brand = Column(String(50))  # 品牌名称
    price = Column(Float)  # 单价
    serial_number = Column(String(50))  # 编号
    create_date = Column(String(50))  # 创建日期
    remarks = Column(String(255))  # 备注说明
    image_url = Column(String(255))  # 图片地址
    weight = Column(String(50))  # 重量
    dimensions = Column(String(50))  # 尺寸规格
    skills = Column(String(255))  # 技能特点
    honors = Column(String(255))  # 获得的荣誉
    origin = Column(String(50))  # 产地

class TaskRecord(Base):
    """任务记录表"""
    __tablename__ = "task_records"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    robot_name = Column(String(50))  # 机器人名称
    task_type = Column(String(50))  # 任务类型
    completion_rate = Column(Float)  # 完成度
    date = Column(DateTime)  # 记录日期

class RobotType(Base):
    """机器人类型表"""
    __tablename__ = "robot_types"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    name = Column(String(50))  # 类型名称
    description = Column(String(255))  # 类型描述

class TrainingField(Base):
    """训练场信息表"""
    __tablename__ = "training_fields"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    name = Column(String(50))  # 训练场名称
    description = Column(String(255))  # 训练场描述
    scene_image_url = Column(String(255))  # 场景图片地址
    monitor_image_url = Column(String(255))  # 监控画面地址

class TrainingRecord(Base):
    """训练记录表"""
    __tablename__ = "training_records"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    robot_id = Column(Integer, ForeignKey("robots.id"))  # 机器人ID
    field_id = Column(Integer, ForeignKey("training_fields.id"))  # 训练场ID
    online = Column(Integer)  # 在线数量
    offline = Column(Integer)  # 离线数量
    fault = Column(Integer)  # 故障数量
    time = Column(String(50))  # 记录时间

class EntryRecord(Base):
    """入场记录表"""
    __tablename__ = "entry_records"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    robot_id = Column(Integer, ForeignKey("robots.id"))  # 机器人ID
    time = Column(String(50))  # 入场时间
    quantity = Column(Integer)  # 入场数量

class AwardRecord(Base):
    """获奖证书表"""
    __tablename__ = "award_records"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    award_name = Column(String(100), nullable=False)  # 奖项名称
    award_level = Column(String(50), nullable=False)  # 奖项级别
    issuing_authority = Column(String(100), nullable=False)  # 颁发机构
    award_date = Column(DateTime, nullable=False)  # 获奖日期
    certificate_image = Column(String(255))  # 证书图片地址
    award_type = Column(String(20), nullable=False)  # 获奖类型：'robot' 或 'field'
    robot_id = Column(Integer, ForeignKey("robots.id", ondelete="CASCADE"))  # 获奖机器人ID（可为空）
    field_id = Column(Integer, ForeignKey("training_fields.id", ondelete="CASCADE"))  # 获奖训练场ID（可为空）
    description = Column(String(255))  # 奖项描述

    robot = relationship("Robot", backref="award_records")  # 关联机器人
    field = relationship("TrainingField", backref="award_records")  # 关联训练场

    __table_args__ = (
        # 确保robot_id和field_id不能同时为空或同时有值
        CheckConstraint('NOT(robot_id IS NULL AND field_id IS NULL) AND NOT(robot_id IS NOT NULL AND field_id IS NOT NULL)',
                       name='check_award_target'),
    )

class ParticipationRecord(Base):
    """参观记录表"""
    __tablename__ = "participation_records"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    visitor_count = Column(Integer)  # 参观人数
    time = Column(String(50))  # 参观时间

class DisplayVideo(Base):
    """展示视频表"""
    __tablename__ = "display_videos"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键ID
    video_url = Column(String(255))  # 视频地址
    description = Column(String(255))  # 视频描述 