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
    robot_type: str = Field(..., description="机器人类型-第一代")
    industry_type: str = Field(..., description="种类-工业机器人")
    product_series: Optional[str] = Field(None, description="品牌-外骨")
    price: Optional[float] = Field(None, description="单价-10000")
    serial_number: str = Field(..., description="编号-89757")
    create_date: str = Field(..., description="创建日期-202503201900")
    status: Optional[str] = Field(None, description="状态：在线/离线/故障")
    training_status: Optional[str] = Field(None, description="训练状态：上线/培训中/上市中")
    skills: Optional[str] = Field(None, description="技能特点")
    awards: Optional[str] = Field(None, description="获得的荣誉")
    product_location: Optional[str] = Field(None, description="产地")
    dimensions: Optional[str] = Field(None, description="参考重量尺寸")
    image_url: Optional[str] = Field(None, description="图片地址")
    remarks: Optional[str] = Field(None, description="备注说明")
    is_active: bool = Field(default=True, description="是否在用")

class RobotCreate(RobotBase):
    pass

class Robot(RobotBase):
    id: int

    class Config:
        from_attributes = True

class TrainingFieldBase(BaseModel):
    name: str = Field(..., description="训练场名称")
    description: Optional[str] = Field(None, description="训练场说明")
    image_url: Optional[str] = Field(None, description="图片地址")

class TrainingFieldCreate(TrainingFieldBase):
    pass

class TrainingField(TrainingFieldBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class CompanyBase(BaseModel):
    name: str = Field(..., description="公司名称")
    description: Optional[str] = Field(None, description="简介")
    address: Optional[str] = Field(None, description="地址")
    contact: Optional[str] = Field(None, description="联系方式")
    expiry_time: Optional[datetime] = Field(None, description="到期时间-202504031600")

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class AwardBase(BaseModel):
    name: str = Field(..., description="荣誉名称")
    description: Optional[str] = Field(None, description="荣誉说明")
    issue_date: Optional[datetime] = Field(None, description="颁发日期")
    image_url: Optional[str] = Field(None, description="证书图片地址")

class AwardCreate(AwardBase):
    pass

class Award(AwardBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class VideoBase(BaseModel):
    title: Optional[str] = Field(None, description="视频标题")
    url: str = Field(..., description="视频地址")
    type: str = Field(..., description="类型：在线流/本地视频")
    description: Optional[str] = Field(None, description="视频描述")

class VideoCreate(VideoBase):
    pass

class Video(VideoBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class VisitorRecordBase(BaseModel):
    visit_date: datetime = Field(..., description="参观日期")
    visitor_count: int = Field(default=0, description="参观人数")

class VisitorRecordCreate(VisitorRecordBase):
    pass

class VisitorRecord(VisitorRecordBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class DataTypeBase(BaseModel):
    name: str = Field(..., description="数据类型名称")
    description: Optional[str] = Field(None, description="类型说明")
    unit: Optional[str] = Field(None, description="单位")

class DataTypeCreate(DataTypeBase):
    pass

class DataType(DataTypeBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class DataRecordBase(BaseModel):
    data_type_id: int = Field(..., description="数据类型ID")
    value: str = Field(..., description="采集的数据值")
    collect_time: datetime = Field(..., description="采集时间")

class DataRecordCreate(DataRecordBase):
    pass

class DataRecord(DataRecordBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class WebConfigBase(BaseModel):
    key: str = Field(..., description="配置键")
    value: Optional[str] = Field(None, description="配置值")
    description: Optional[str] = Field(None, description="配置说明")

class WebConfigCreate(WebConfigBase):
    pass

class WebConfig(WebConfigBase):
    id: int
    create_time: datetime
    update_time: Optional[datetime]

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
    create_time: datetime

    class Config:
        from_attributes = True

class ParticipationRecordBase(BaseModel):
    visitor_count: int = Field(..., description="参观人数")
    time: datetime = Field(default_factory=datetime.now, description="参观时间")

class ParticipationRecordCreate(ParticipationRecordBase):
    pass

class ParticipationRecord(ParticipationRecordBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    robot_types: Dict[str, int] = Field(..., description="机器人类型分布")
    training_field_stats: List[Dict[str, Any]] = Field(..., description="训练场统计")
    robot_status: Dict[str, int] = Field(..., description="机器人状态统计")
    robot_skills: Dict[str, int] = Field(..., description="机器人技能分布")
    participation_trend: List[Dict[str, Any]] = Field(..., description="参观人数趋势") 