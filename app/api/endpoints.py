from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.models import models
from app.schemas import schemas
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    # Get robot type distribution
    robot_types = db.query(
        models.Robot.body_type,
        func.count(models.Robot.id)
    ).group_by(models.Robot.body_type).all()
    
    robot_types_dict = {type_: count for type_, count in robot_types}

    # Get training field statistics
    training_fields = db.query(models.TrainingField).all()
    training_field_stats = []
    for field in training_fields:
        stats = db.query(models.TrainingRecord).filter(
            models.TrainingRecord.field_id == field.id
        ).first()
        if stats:
            training_field_stats.append({
                "name": field.name,
                "online": stats.online,
                "offline": stats.offline,
                "fault": stats.fault
            })

    # Get robot status statistics
    status_stats = db.query(
        func.sum(models.TrainingRecord.online).label("online"),
        func.sum(models.TrainingRecord.offline).label("offline"),
        func.sum(models.TrainingRecord.fault).label("fault")
    ).first()

    robot_status = {
        "online": status_stats[0] or 0,
        "offline": status_stats[1] or 0,
        "fault": status_stats[2] or 0
    }

    # Get robot skills distribution
    robot_skills = db.query(
        models.Robot.skills,
        func.count(models.Robot.id)
    ).group_by(models.Robot.skills).all()
    
    skills_dict = {skill: count for skill, count in robot_skills}

    # Get visitor trend
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    
    participation_records = db.query(
        models.ParticipationRecord.time,
        models.ParticipationRecord.visitor_count
    ).filter(
        models.ParticipationRecord.time >= seven_days_ago.strftime("%Y%m%d")
    ).order_by(models.ParticipationRecord.time).all()

    participation_trend = [
        {"date": record[0], "count": record[1]}
        for record in participation_records
    ]

    return schemas.DashboardStats(
        robot_types=robot_types_dict,
        training_field_stats=training_field_stats,
        robot_status=robot_status,
        robot_skills=skills_dict,
        participation_trend=participation_trend
    )

@router.get("/robots", response_model=List[schemas.Robot])
def get_robots(db: Session = Depends(get_db)):
    """获取所有机器人列表"""
    return db.query(models.Robot).all()

@router.get("/robots/{robot_id}", response_model=schemas.Robot)
def get_robot(robot_id: int, db: Session = Depends(get_db)):
    """获取单个机器人详情"""
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    return robot

@router.post("/robots", response_model=schemas.Robot)
def create_robot(robot: schemas.RobotCreate, db: Session = Depends(get_db)):
    """创建新机器人"""
    db_robot = models.Robot(**robot.model_dump())
    db.add(db_robot)
    db.commit()
    db.refresh(db_robot)
    return db_robot

@router.put("/robots/{robot_id}", response_model=schemas.Robot)
def update_robot(robot_id: int, robot: schemas.RobotCreate, db: Session = Depends(get_db)):
    """更新机器人信息"""
    db_robot = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
    if not db_robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    for key, value in robot.model_dump().items():
        setattr(db_robot, key, value)
    
    db.commit()
    db.refresh(db_robot)
    return db_robot

@router.delete("/robots/{robot_id}")
def delete_robot(robot_id: int, db: Session = Depends(get_db)):
    """删除机器人"""
    db_robot = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
    if not db_robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    db.delete(db_robot)
    db.commit()
    return {"message": "Robot deleted successfully"}

@router.get("/training-fields", response_model=List[schemas.TrainingField])
def get_training_fields(db: Session = Depends(get_db)):
    """获取所有训练场列表"""
    return db.query(models.TrainingField).all()

@router.get("/training-fields/{field_id}", response_model=schemas.TrainingField)
def get_training_field(field_id: int, db: Session = Depends(get_db)):
    """获取单个训练场详情"""
    field = db.query(models.TrainingField).filter(models.TrainingField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Training field not found")
    return field

@router.post("/training-fields", response_model=schemas.TrainingField)
def create_training_field(field: schemas.TrainingFieldCreate, db: Session = Depends(get_db)):
    """创建新训练场"""
    db_field = models.TrainingField(**field.model_dump())
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field

@router.get("/training-records", response_model=List[schemas.TrainingRecord])
def get_training_records(db: Session = Depends(get_db)):
    return db.query(models.TrainingRecord).all()

@router.get("/awards", response_model=List[schemas.Award])
def get_awards(db: Session = Depends(get_db)):
    """获取所有荣誉证书列表"""
    try:
        logger.info("Fetching all awards")
        awards = db.query(models.Award).all()
        logger.info(f"Found {len(awards)} awards")
        return awards
    except Exception as e:
        logger.error(f"Error fetching awards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/awards/{award_id}", response_model=schemas.Award)
def get_award(award_id: int, db: Session = Depends(get_db)):
    """获取单个荣誉证书详情"""
    award = db.query(models.Award).filter(models.Award.id == award_id).first()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    return award

@router.post("/awards", response_model=schemas.Award)
def create_award(award: schemas.AwardCreate, db: Session = Depends(get_db)):
    """创建新荣誉证书"""
    db_award = models.Award(**award.model_dump())
    db.add(db_award)
    db.commit()
    db.refresh(db_award)
    return db_award

@router.put("/awards/{award_id}", response_model=schemas.Award)
def update_award(award_id: int, award: schemas.AwardCreate, db: Session = Depends(get_db)):
    """更新荣誉证书信息"""
    db_award = db.query(models.Award).filter(models.Award.id == award_id).first()
    if not db_award:
        raise HTTPException(status_code=404, detail="Award not found")
    
    for key, value in award.model_dump().items():
        setattr(db_award, key, value)
    
    db.commit()
    db.refresh(db_award)
    return db_award

@router.delete("/awards/{award_id}")
def delete_award(award_id: int, db: Session = Depends(get_db)):
    """删除荣誉证书"""
    db_award = db.query(models.Award).filter(models.Award.id == award_id).first()
    if not db_award:
        raise HTTPException(status_code=404, detail="Award not found")
    
    db.delete(db_award)
    db.commit()
    return {"message": "Award deleted successfully"}

@router.get("/companies", response_model=List[schemas.Company])
def get_companies(db: Session = Depends(get_db)):
    """获取所有公司列表"""
    return db.query(models.Company).all()

@router.get("/companies/{company_id}", response_model=schemas.Company)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """获取单个公司详情"""
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.post("/companies", response_model=schemas.Company)
def create_company(company: schemas.CompanyCreate, db: Session = Depends(get_db)):
    """创建新公司"""
    db_company = models.Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

@router.get("/videos", response_model=List[schemas.Video])
def get_videos(db: Session = Depends(get_db)):
    """获取所有视频列表"""
    return db.query(models.Video).all()

@router.post("/videos", response_model=schemas.Video)
def create_video(video: schemas.VideoCreate, db: Session = Depends(get_db)):
    """创建新视频"""
    db_video = models.Video(**video.model_dump())
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

@router.get("/visitor-records", response_model=List[schemas.VisitorRecord])
def get_visitor_records(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """获取参观记录列表，支持日期范围筛选"""
    query = db.query(models.VisitorRecord)
    
    if start_date:
        query = query.filter(models.VisitorRecord.visit_date >= start_date)
    if end_date:
        query = query.filter(models.VisitorRecord.visit_date <= end_date)
    
    return query.order_by(models.VisitorRecord.visit_date.desc()).all()

@router.post("/visitor-records", response_model=schemas.VisitorRecord)
def create_visitor_record(record: schemas.VisitorRecordCreate, db: Session = Depends(get_db)):
    """创建新参观记录"""
    db_record = models.VisitorRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@router.get("/data-types", response_model=List[schemas.DataType])
def get_data_types(db: Session = Depends(get_db)):
    """获取所有数据类型列表"""
    return db.query(models.DataType).all()

@router.post("/data-types", response_model=schemas.DataType)
def create_data_type(data_type: schemas.DataTypeCreate, db: Session = Depends(get_db)):
    """创建新数据类型"""
    db_data_type = models.DataType(**data_type.model_dump())
    db.add(db_data_type)
    db.commit()
    db.refresh(db_data_type)
    return db_data_type

@router.get("/data-records", response_model=List[schemas.DataRecord])
def get_data_records(
    data_type_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """获取数据记录列表，支持按类型和时间范围筛选"""
    query = db.query(models.DataRecord)
    
    if data_type_id:
        query = query.filter(models.DataRecord.data_type_id == data_type_id)
    if start_time:
        query = query.filter(models.DataRecord.collect_time >= start_time)
    if end_time:
        query = query.filter(models.DataRecord.collect_time <= end_time)
    
    return query.order_by(models.DataRecord.collect_time.desc()).all()

@router.post("/data-records", response_model=schemas.DataRecord)
def create_data_record(record: schemas.DataRecordCreate, db: Session = Depends(get_db)):
    """创建新数据记录"""
    db_record = models.DataRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@router.get("/web-configs", response_model=List[schemas.WebConfig])
def get_web_configs(db: Session = Depends(get_db)):
    """获取所有网页配置"""
    return db.query(models.WebConfig).all()

@router.get("/web-configs/{key}", response_model=schemas.WebConfig)
def get_web_config(key: str, db: Session = Depends(get_db)):
    """获取指定键的网页配置"""
    config = db.query(models.WebConfig).filter(models.WebConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.post("/web-configs", response_model=schemas.WebConfig)
def create_web_config(config: schemas.WebConfigCreate, db: Session = Depends(get_db)):
    """创建新网页配置"""
    db_config = models.WebConfig(**config.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.put("/web-configs/{key}", response_model=schemas.WebConfig)
def update_web_config(key: str, config: schemas.WebConfigCreate, db: Session = Depends(get_db)):
    """更新网页配置"""
    db_config = db.query(models.WebConfig).filter(models.WebConfig.key == key).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    for k, v in config.model_dump().items():
        setattr(db_config, k, v)
    
    db.commit()
    db.refresh(db_config)
    return db_config 