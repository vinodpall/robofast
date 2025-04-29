from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any, ForwardRef, Generic, TypeVar, Union
from enum import Enum
from pydantic import validator

# 定义泛型类型变量
T = TypeVar('T')

# 分页响应模型
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

# 1. 基础枚举类型
class RobotBodyType(str, Enum):
    """机器人体型类别枚举"""
    HUMANOID = "humanoid"  # 人形机器人
    WHEELED = "wheeled"    # 轮式机器人
    QUADRUPED = "quadruped"  # 四足机器人
    AERIAL = "aerial"      # 空中机器人
    OTHER = "other"        # 其他类型

# 2. 基础模型类
class CompanyBase(BaseModel):
    name: str = Field(..., description="公司名称")
    description: Optional[str] = Field(None, description="简介")
    is_carousel: bool = Field(default=False, description="是否轮播")
    create_time: Optional[str] = Field(None, description="创建时间-202504031600")

class TrainingFieldBase(BaseModel):
    name: str = Field(..., description="训练场名称")
    description: Optional[str] = Field(None, description="训练场简介")
    image_url: Optional[str] = Field(None, description="场景图片URL")

class AwardBase(BaseModel):
    name: str = Field(..., description="荣誉名称")
    description: Optional[str] = Field(None, description="荣誉简介")
    image_url: Optional[str] = Field(None, description="图片URL")
    is_carousel: bool = Field(default=False, description="是否轮播")

class DataTypeBase(BaseModel):
    name: str = Field(..., description="数据类型名称")

class RobotBase(BaseModel):
    name: str = Field(..., description="机器人名称")
    industry_type: str = Field(..., description="种类-工业机器人")
    company_id: int = Field(..., description="品牌-外键关联公司表")
    price: Optional[float] = Field(None, description="单价-10000")
    serial_number: str = Field(..., description="编号-89757")
    create_date: Optional[Union[str, int]] = Field(None, description="创建时间")
    status: Optional[str] = Field(None, description="状态：在线/离线/故障")
    skills: Optional[str] = Field(None, description="技能特点")
    product_location: Optional[str] = Field(None, description="产地")
    dimensions: Optional[str] = Field(None, description="参考重量尺寸")
    image_url: Optional[str] = Field(None, description="图片地址")
    remarks: Optional[str] = Field(None, description="备注说明")
    training_field_id: Optional[int] = Field(None, description="训练场-外键关联训练场表")
    awards: Optional[str] = Field(None, description="荣誉-字符串形式")
    recommendation_reason: Optional[str] = Field(None, description="推荐理由")
    is_carousel: bool = Field(default=False, description="是否轮播")
    carousel_add_time: Optional[Union[str, int]] = Field(None, description="加入轮播时间")

    @validator('image_url')
    def validate_image_url(cls, v):
        if not v:
            return v
        # 如果包含域名，只保留路径部分
        if '://' in v:
            v = v.split('://', 1)[1].split('/', 1)[1]
        # 确保路径以 /static 开头，但避免重复添加
        if not v.startswith('/static/'):
            v = f"/static/{v.lstrip('/')}"
        return v

    @validator('create_date')
    def validate_create_date(cls, v):
        if not v:
            return v
        try:
            if isinstance(v, str):
                # 尝试不同的日期格式
                formats = ["%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
                for fmt in formats:
                    try:
                        datetime.strptime(v, fmt)
                        return v
                    except ValueError:
                        continue
            elif isinstance(v, int):
                # 验证时间戳
                datetime.fromtimestamp(v)
                return v
            # 如果字符串是纯数字，也允许
            if isinstance(v, str) and v.isdigit():
                return v
            raise ValueError("创建日期格式错误")
        except Exception:
            raise ValueError("创建日期格式错误")

    @validator('carousel_add_time')
    def validate_carousel_add_time(cls, v):
        if not v:
            return v
        try:
            if isinstance(v, str):
                # 尝试不同的日期格式
                formats = ["%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M", "%H"]
                for fmt in formats:
                    try:
                        datetime.strptime(v, fmt)
                        return v
                    except ValueError:
                        continue
                # 如果字符串是纯数字，也允许
                if v.isdigit():
                    return v
            elif isinstance(v, int):
                # 验证时间戳
                datetime.fromtimestamp(v)
                return v
            raise ValueError("轮播时间格式错误")
        except Exception:
            raise ValueError("轮播时间格式错误")

# 3. 创建模型类
class AwardCreate(AwardBase):
    pass

class DataTypeCreate(DataTypeBase):
    pass

class DataRecordBase(BaseModel):
    data_type_id: Optional[int] = Field(None, description="数据类型-外键关联数据类型表")
    collect_date: str = Field(..., description="时间-20250402")
    robot_id: int = Field(..., description="机器人-外键关联机器人表")
    count: int = Field(..., description="数量")

class DataRecordCreate(DataRecordBase):
    pass

class DataRecord(DataRecordBase):
    id: int
    data_type: Optional["DataType"] = None
    robot: Optional["RobotBase"] = None

    class Config:
        from_attributes = True

class RobotCreate(RobotBase):
    pass

class TrainingFieldCreate(TrainingFieldBase):
    pass

class CompanyCreate(CompanyBase):
    award_ids: Optional[List[int]] = Field(default=None, description="荣誉ID列表")

# 4. 完整模型类
class Award(AwardBase):
    id: int

    class Config:
        from_attributes = True

class DataType(DataTypeBase):
    id: int

    class Config:
        from_attributes = True

class Robot(RobotBase):
    id: int
    company: Optional[CompanyBase] = None
    training_field: Optional[TrainingFieldBase] = None
    data_records: List[DataRecord] = []

    class Config:
        from_attributes = True

class TrainingField(TrainingFieldBase):
    id: int

    class Config:
        from_attributes = True

class Company(CompanyBase):
    id: int
    awards: List[Award] = []

    class Config:
        from_attributes = True

# 5. 其他模型类
class VideoBase(BaseModel):
    name: str = Field(..., description="视频名称")
    description: Optional[str] = Field(None, description="视频简介")
    url: Optional[str] = Field(None, description="视频URL")
    type: Optional[str] = Field(None, description="视频类型")
    is_carousel: bool = Field(default=False, description="是否轮播")
    carousel_add_time: Optional[str] = Field(None, description="加入轮播时间")
    create_time: Optional[str] = Field(None, description="创建时间-时间戳字符串")

    @validator('url')
    def validate_url(cls, v):
        if not v:
            return v
        return v

class VideoCreate(VideoBase):
    pass

class Video(VideoBase):
    id: int

    class Config:
        from_attributes = True

class VisitorRecordBase(BaseModel):
    visitor_count: int = Field(default=0, description="参观人数")
    visit_date: str = Field(..., description="时间-20250420")

class VisitorRecordCreate(VisitorRecordBase):
    pass

class VisitorRecord(VisitorRecordBase):
    id: int

    class Config:
        from_attributes = True

class WebConfigBase(BaseModel):
    name: str = Field(..., description="网页名称")
    icon_url: Optional[str] = Field(None, description="图标URL")
    video_carousel: bool = Field(default=False, description="视频是否轮播")
    page_carousel: bool = Field(default=False, description="网页是否轮播")
    current_carousel_page: Optional[int] = Field(None, description="当前轮播页")
    first_page_duration: Optional[int] = Field(None, description="第一页停留时间(秒)")
    second_page_duration: Optional[int] = Field(None, description="第二页停留时间(秒)")
    third_page_duration: Optional[int] = Field(None, description="第三页停留时间(秒)")
    visitor_count: Optional[int] = Field(None, description="来访人数统计")
    weekly_visitor_count: Optional[int] = Field(None, description="本周访客数")
    monthly_visitor_count: Optional[int] = Field(None, description="本月访客数")
    video_carousel_duration: Optional[int] = Field(None, description="视频轮播停留时间(秒)")

class WebConfigCreate(WebConfigBase):
    pass

class WebConfig(WebConfigBase):
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

class FileResponse(BaseModel):
    """文件上传响应模型"""
    url: str
    
    class Config:
        from_attributes = True

# 6. 更新前向引用
Robot.model_rebuild()
DataRecord.model_rebuild() 