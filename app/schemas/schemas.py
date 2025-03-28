from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import validator

class RobotBodyType(str, Enum):
    """机器人体型类别枚举"""
    HUMANOID = "humanoid"  # 人形机器人
    WHEELED = "wheeled"    # 轮式机器人
    QUADRUPED = "quadruped"  # 四足机器人
    AERIAL = "aerial"      # 空中机器人
    OTHER = "other"        # 其他类型

class RobotBase(BaseModel):
    name: str = Field(..., description="机器人名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数配置")
    body_type: RobotBodyType = Field(..., description="机器人体型类别")
    brand: str = Field(..., description="品牌名称")
    price: float = Field(..., description="单价")
    serial_number: str = Field(..., description="编号")
    create_date: datetime = Field(default_factory=datetime.now, description="创建日期")
    remarks: Optional[str] = Field(None, description="备注说明")
    image_url: Optional[str] = Field(None, description="图片地址")
    weight: Optional[float] = Field(None, description="重量(kg)")
    length: Optional[float] = Field(None, description="长度(mm)")
    width: Optional[float] = Field(None, description="宽度(mm)")
    height: Optional[float] = Field(None, description="高度(mm)")
    skills: List[str] = Field(default_factory=list, description="技能特点")
    origin: str = Field(..., description="产地")

class RobotCreate(RobotBase):
    pass

class Robot(RobotBase):
    id: int

    class Config:
        from_attributes = True

class TrainingFieldBase(BaseModel):
    name: str = Field(..., description="训练场名称")
    description: Optional[str] = Field(None, description="训练场描述")
    scene_image_url: Optional[str] = Field(None, description="场景图片地址")
    monitor_image_url: Optional[str] = Field(None, description="监控画面地址")

class TrainingFieldCreate(TrainingFieldBase):
    pass

class TrainingField(TrainingFieldBase):
    id: int

    class Config:
        from_attributes = True

class TrainingRecordBase(BaseModel):
    robot_id: int = Field(..., description="机器人ID")
    field_id: int = Field(..., description="训练场ID")
    online: int = Field(default=0, description="在线数量")
    offline: int = Field(default=0, description="离线数量")
    fault: int = Field(default=0, description="故障数量")
    time: datetime = Field(default_factory=datetime.now, description="记录时间")

class TrainingRecordCreate(TrainingRecordBase):
    pass

class TrainingRecord(TrainingRecordBase):
    id: int

    class Config:
        from_attributes = True

class AwardType(str, Enum):
    """获奖类型枚举"""
    ROBOT = "robot"  # 机器人获奖
    FIELD = "field"  # 训练场获奖

class AwardRecordBase(BaseModel):
    award_name: str = Field(..., description="奖项名称")
    award_level: str = Field(..., description="奖项级别")
    issuing_authority: str = Field(..., description="颁发机构")
    award_date: datetime = Field(..., description="获奖日期")
    certificate_image: Optional[str] = Field(None, description="证书图片地址")
    award_type: AwardType = Field(..., description="获奖类型：robot或field")
    robot_id: Optional[int] = Field(None, description="获奖机器人ID")
    field_id: Optional[int] = Field(None, description="获奖训练场ID")
    description: Optional[str] = Field(None, description="奖项描述")

    @validator('robot_id', 'field_id')
    def validate_ids(cls, v, values):
        if 'award_type' in values:
            if values['award_type'] == AwardType.ROBOT and not v and 'robot_id' in values.keys():
                raise ValueError('robot_id is required when award_type is robot')
            if values['award_type'] == AwardType.FIELD and not v and 'field_id' in values.keys():
                raise ValueError('field_id is required when award_type is field')
        return v

class AwardRecordCreate(AwardRecordBase):
    pass

class AwardRecord(AwardRecordBase):
    id: int

    class Config:
        from_attributes = True

class ParticipationRecordBase(BaseModel):
    visitor_count: int = Field(..., description="参观人数")
    time: datetime = Field(default_factory=datetime.now, description="参观时间")

class ParticipationRecordCreate(ParticipationRecordBase):
    pass

class ParticipationRecord(ParticipationRecordBase):
    id: int

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    robot_types: Dict[str, int] = Field(..., description="机器人类型分布")
    training_field_stats: List[Dict[str, Any]] = Field(..., description="训练场统计")
    robot_status: Dict[str, int] = Field(..., description="机器人状态统计")
    robot_skills: Dict[str, int] = Field(..., description="机器人技能分布")
    participation_trend: List[Dict[str, Any]] = Field(..., description="参观人数趋势") 