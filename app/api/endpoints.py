from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.models import models
from app.schemas import schemas
from sqlalchemy import func
from datetime import datetime, timedelta

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
    return db.query(models.Robot).all()

@router.get("/training-fields", response_model=List[schemas.TrainingField])
def get_training_fields(db: Session = Depends(get_db)):
    return db.query(models.TrainingField).all()

@router.get("/training-records", response_model=List[schemas.TrainingRecord])
def get_training_records(db: Session = Depends(get_db)):
    return db.query(models.TrainingRecord).all()

@router.get("/awards", response_model=List[schemas.AwardRecord])
def get_awards(
    db: Session = Depends(get_db),
    award_type: Optional[schemas.AwardType] = None,
    robot_id: Optional[int] = None,
    field_id: Optional[int] = None
):
    """获取奖项记录，支持按类型和ID筛选"""
    query = db.query(models.AwardRecord)
    
    if award_type:
        query = query.filter(models.AwardRecord.award_type == award_type)
    if robot_id:
        query = query.filter(models.AwardRecord.robot_id == robot_id)
    if field_id:
        query = query.filter(models.AwardRecord.field_id == field_id)
    
    return query.order_by(models.AwardRecord.award_date.desc()).all()

@router.get("/awards/robot/{robot_id}", response_model=List[schemas.AwardRecord])
def get_robot_awards(robot_id: int, db: Session = Depends(get_db)):
    """获取指定机器人的所有奖项记录"""
    awards = db.query(models.AwardRecord).filter(
        models.AwardRecord.robot_id == robot_id,
        models.AwardRecord.award_type == 'robot'
    ).order_by(models.AwardRecord.award_date.desc()).all()
    
    if not awards:
        raise HTTPException(status_code=404, detail="No awards found for this robot")
    return awards

@router.get("/awards/field/{field_id}", response_model=List[schemas.AwardRecord])
def get_field_awards(field_id: int, db: Session = Depends(get_db)):
    """获取指定训练场的所有奖项记录"""
    awards = db.query(models.AwardRecord).filter(
        models.AwardRecord.field_id == field_id,
        models.AwardRecord.award_type == 'field'
    ).order_by(models.AwardRecord.award_date.desc()).all()
    
    if not awards:
        raise HTTPException(status_code=404, detail="No awards found for this training field")
    return awards

@router.post("/awards", response_model=schemas.AwardRecord)
def create_award(award: schemas.AwardRecordCreate, db: Session = Depends(get_db)):
    """创建新的奖项记录"""
    # 根据award_type验证关联ID
    if award.award_type == schemas.AwardType.ROBOT:
        if not db.query(models.Robot).filter(models.Robot.id == award.robot_id).first():
            raise HTTPException(status_code=404, detail="Robot not found")
    else:  # award_type == schemas.AwardType.FIELD
        if not db.query(models.TrainingField).filter(models.TrainingField.id == award.field_id).first():
            raise HTTPException(status_code=404, detail="Training field not found")
    
    db_award = models.AwardRecord(**award.model_dump())
    db.add(db_award)
    db.commit()
    db.refresh(db_award)
    return db_award

@router.put("/awards/{award_id}", response_model=schemas.AwardRecord)
def update_award(award_id: int, award: schemas.AwardRecordCreate, db: Session = Depends(get_db)):
    """更新奖项记录"""
    db_award = db.query(models.AwardRecord).filter(models.AwardRecord.id == award_id).first()
    if not db_award:
        raise HTTPException(status_code=404, detail="Award not found")
    
    # 根据award_type验证关联ID
    if award.award_type == schemas.AwardType.ROBOT:
        if not db.query(models.Robot).filter(models.Robot.id == award.robot_id).first():
            raise HTTPException(status_code=404, detail="Robot not found")
    else:  # award_type == schemas.AwardType.FIELD
        if not db.query(models.TrainingField).filter(models.TrainingField.id == award.field_id).first():
            raise HTTPException(status_code=404, detail="Training field not found")
    
    for key, value in award.model_dump().items():
        setattr(db_award, key, value)
    
    db.commit()
    db.refresh(db_award)
    return db_award

@router.delete("/awards/{award_id}")
def delete_award(award_id: int, db: Session = Depends(get_db)):
    """删除奖项记录"""
    db_award = db.query(models.AwardRecord).filter(models.AwardRecord.id == award_id).first()
    if not db_award:
        raise HTTPException(status_code=404, detail="Award not found")
    
    db.delete(db_award)
    db.commit()
    return {"message": "Award deleted successfully"} 