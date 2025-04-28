from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database.database import get_db
from app.models import models
from app.schemas import schemas
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import logging
from app.utils.file_handler import save_upload_file

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    # Get robot type distribution
    robot_types = db.query(
        models.Robot.industry_type,
        func.count(models.Robot.id)
    ).group_by(models.Robot.industry_type).all()
    
    robot_types_dict = {type_: count for type_, count in robot_types}

    # Get training field statistics
    training_fields = db.query(models.TrainingField).all()
    training_field_stats = []
    for field in training_fields:
        robot_count = db.query(func.count(models.Robot.id)).filter(
            models.Robot.training_field_id == field.id
        ).scalar()
        
        training_field_stats.append({
            "name": field.name,
            "robot_count": robot_count
        })

    # Get robot status statistics
    status_stats = db.query(
        models.Robot.status,
        func.count(models.Robot.id)
    ).group_by(models.Robot.status).all()
    
    robot_status = {status: count for status, count in status_stats}

    # Get robot skills distribution
    robot_skills = db.query(
        models.Robot.skills,
        func.count(models.Robot.id)
    ).group_by(models.Robot.skills).all()
    
    skills_dict = {skill: count for skill, count in robot_skills if skill}

    # Get visitor trend
    visitor_records = db.query(
        models.VisitorRecord.visit_date,
        models.VisitorRecord.visitor_count
    ).order_by(models.VisitorRecord.visit_date).all()

    participation_trend = [
        {"date": record[0], "count": record[1]}
        for record in visitor_records
    ]

    return schemas.DashboardStats(
        robot_types=robot_types_dict,
        training_field_stats=training_field_stats,
        robot_status=robot_status,
        robot_skills=skills_dict,
        participation_trend=participation_trend
    )

@router.get("/robots", response_model=schemas.PaginatedResponse[schemas.Robot])
def get_robots(
    page: int = 1,
    page_size: int = 10,
    name_or_serial: Optional[str] = None,
    industry_type: Optional[str] = None,
    training_field_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取所有机器人列表"""
    try:
        logger.info(f"获取机器人列表: page={page}, page_size={page_size}")
        
        # 构建基础查询
        query = db.query(models.Robot).options(
            joinedload(models.Robot.company),
            joinedload(models.Robot.training_field),
            joinedload(models.Robot.data_records)
        )
        
        # 添加筛选条件
        if name_or_serial:
            query = query.filter(
                or_(
                    models.Robot.name.ilike(f"%{name_or_serial}%"),
                    models.Robot.serial_number.ilike(f"%{name_or_serial}%")
                )
            )
        
        if industry_type:
            query = query.filter(models.Robot.industry_type == industry_type)
        
        if training_field_id:
            query = query.filter(models.Robot.training_field_id == training_field_id)
        
        if status:
            query = query.filter(models.Robot.status == status)
        
        if start_date:
            query = query.filter(models.Robot.create_date >= start_date)
        
        if end_date:
            query = query.filter(models.Robot.create_date <= end_date)
        
        # 计算总数
        total = query.count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        robots = query.order_by(models.Robot.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(robots)} 个机器人")
        
        return schemas.PaginatedResponse(
            items=robots,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取机器人列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/robots/{robot_id}", response_model=schemas.Robot)
def get_robot(robot_id: int, db: Session = Depends(get_db)):
    """获取单个机器人详情"""
    try:
        logger.info(f"获取机器人详情: ID={robot_id}")
        robot = db.query(models.Robot).options(
            joinedload(models.Robot.company),
            joinedload(models.Robot.training_field),
            joinedload(models.Robot.data_records)
        ).filter(models.Robot.id == robot_id).first()
        if not robot:
            logger.warning(f"未找到机器人: ID={robot_id}")
            raise HTTPException(status_code=404, detail="Robot not found")
        return robot
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取机器人详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/robots", response_model=schemas.Robot)
def create_robot(robot: schemas.RobotCreate, db: Session = Depends(get_db)):
    """创建新机器人"""
    try:
        logger.info("创建新机器人")
        
        # 验证必填字段
        if not robot.name:
            raise HTTPException(status_code=422, detail="机器人名称不能为空")
        if not robot.industry_type:
            raise HTTPException(status_code=422, detail="机器人类型不能为空")
        if not robot.company_id:
            raise HTTPException(status_code=422, detail="所属公司不能为空")
        if not robot.serial_number:
            raise HTTPException(status_code=422, detail="序列号不能为空")
        
        # 验证公司是否存在
        company = db.query(models.Company).filter(models.Company.id == robot.company_id).first()
        if not company:
            logger.warning(f"未找到公司: ID={robot.company_id}")
            raise HTTPException(status_code=404, detail=f"未找到ID为{robot.company_id}的公司")
        
        # 验证训练场是否存在（如果提供了训练场ID）
        if robot.training_field_id:
            field = db.query(models.TrainingField).filter(models.TrainingField.id == robot.training_field_id).first()
            if not field:
                logger.warning(f"未找到训练场: ID={robot.training_field_id}")
                raise HTTPException(status_code=404, detail=f"未找到ID为{robot.training_field_id}的训练场")
        
        # 验证价格（如果提供）
        if robot.price is not None:
            try:
                price = float(robot.price)
                if price < 0:
                    raise HTTPException(status_code=422, detail="价格不能为负数")
            except ValueError:
                raise HTTPException(status_code=422, detail="价格必须是有效的数字")
        
        # 设置默认值
        robot_data = robot.model_dump()
        if not robot_data.get('create_date'):
            robot_data['create_date'] = str(int(datetime.now().timestamp()))
        if not robot_data.get('carousel_add_time'):
            robot_data['carousel_add_time'] = "5"
        
        # 创建机器人
        db_robot = models.Robot(**robot_data)
        db.add(db_robot)
        db.commit()
        db.refresh(db_robot)
        
        logger.info(f"机器人创建成功: ID={db_robot.id}")
        return db_robot
        
    except HTTPException as he:
        raise he
    except ValueError as ve:
        logger.error(f"数据验证失败: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"创建机器人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建机器人失败: {str(e)}")

@router.put("/robots/{robot_id}", response_model=schemas.Robot)
def update_robot(robot_id: int, robot: schemas.RobotCreate, db: Session = Depends(get_db)):
    """更新机器人信息"""
    try:
        logger.info(f"更新机器人: ID={robot_id}")
        db_robot = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
        if not db_robot:
            logger.warning(f"未找到机器人: ID={robot_id}")
            raise HTTPException(status_code=404, detail="Robot not found")
        
        # 验证公司是否存在
        if not db.query(models.Company).filter(models.Company.id == robot.company_id).first():
            raise HTTPException(status_code=404, detail="Company not found")
        
        # 验证训练场是否存在（如果提供了训练场ID）
        if robot.training_field_id and not db.query(models.TrainingField).filter(
            models.TrainingField.id == robot.training_field_id
        ).first():
            raise HTTPException(status_code=404, detail="Training field not found")
        
        # 设置默认值
        robot_data = robot.model_dump()
        if not robot_data.get('create_date'):
            robot_data['create_date'] = str(int(datetime.now().timestamp()))
        if not robot_data.get('carousel_add_time'):
            robot_data['carousel_add_time'] = "5"
        
        for key, value in robot_data.items():
            setattr(db_robot, key, value)
        
        db.commit()
        db.refresh(db_robot)
        logger.info(f"机器人更新成功: ID={robot_id}")
        return db_robot
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"更新机器人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/robots/{robot_id}")
def delete_robot(robot_id: int, db: Session = Depends(get_db)):
    """删除机器人"""
    try:
        logger.info(f"删除机器人: ID={robot_id}")
        db_robot = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
        if not db_robot:
            logger.warning(f"未找到机器人: ID={robot_id}")
            raise HTTPException(status_code=404, detail="Robot not found")
        
        db.delete(db_robot)
        db.commit()
        logger.info(f"机器人删除成功: ID={robot_id}")
        return {"message": "Robot deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"删除机器人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/training-fields", response_model=schemas.PaginatedResponse[schemas.TrainingField])
def get_training_fields(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """获取所有训练场列表"""
    try:
        logger.info(f"获取训练场列表: page={page}, page_size={page_size}")
        
        # 计算总数
        total = db.query(models.TrainingField).count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        fields = db.query(models.TrainingField).options(
            joinedload(models.TrainingField.robots)
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(fields)} 个训练场")
        
        return schemas.PaginatedResponse(
            items=fields,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取训练场列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/training-fields/{field_id}", response_model=schemas.TrainingField)
def get_training_field(field_id: int, db: Session = Depends(get_db)):
    """获取单个训练场详情"""
    try:
        logger.info(f"获取训练场详情: ID={field_id}")
        field = db.query(models.TrainingField).options(
            joinedload(models.TrainingField.robots)
        ).filter(models.TrainingField.id == field_id).first()
        if not field:
            logger.warning(f"未找到训练场: ID={field_id}")
            raise HTTPException(status_code=404, detail="Training field not found")
        return field
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取训练场详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/training-fields", response_model=schemas.TrainingField)
def create_training_field(field: schemas.TrainingFieldCreate, db: Session = Depends(get_db)):
    """创建新训练场"""
    db_field = models.TrainingField(**field.model_dump())
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field

@router.put("/training-fields/{field_id}", response_model=schemas.TrainingField)
def update_training_field(field_id: int, field: schemas.TrainingFieldCreate, db: Session = Depends(get_db)):
    """更新训练场信息"""
    db_field = db.query(models.TrainingField).filter(models.TrainingField.id == field_id).first()
    if not db_field:
        raise HTTPException(status_code=404, detail="Training field not found")
    
    for key, value in field.model_dump().items():
        setattr(db_field, key, value)
    
    db.commit()
    db.refresh(db_field)
    return db_field

@router.delete("/training-fields/{field_id}")
def delete_training_field(field_id: int, db: Session = Depends(get_db)):
    """删除训练场"""
    db_field = db.query(models.TrainingField).filter(models.TrainingField.id == field_id).first()
    if not db_field:
        raise HTTPException(status_code=404, detail="Training field not found")
    
    db.delete(db_field)
    db.commit()
    return {"message": "Training field deleted successfully"}

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

@router.get("/companies", response_model=schemas.PaginatedResponse[schemas.Company])
def get_companies(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """获取所有公司列表"""
    try:
        logger.info(f"获取公司列表: page={page}, page_size={page_size}")
        
        # 计算总数
        total = db.query(models.Company).count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        companies = db.query(models.Company).options(
            joinedload(models.Company.awards)
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(companies)} 个公司")
        
        return schemas.PaginatedResponse(
            items=companies,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取公司列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/companies/{company_id}", response_model=schemas.Company)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """获取单个公司详情"""
    try:
        logger.info(f"获取公司详情: ID={company_id}")
        company = db.query(models.Company).options(
            joinedload(models.Company.awards)
        ).filter(models.Company.id == company_id).first()
        if not company:
            logger.warning(f"未找到公司: ID={company_id}")
            raise HTTPException(status_code=404, detail="Company not found")
        return company
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取公司详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/companies", response_model=schemas.Company)
def create_company(company: schemas.CompanyCreate, db: Session = Depends(get_db)):
    """创建新公司"""
    try:
        logger.info("创建新公司")
        db_company = models.Company(**{k: v for k, v in company.model_dump().items() if k != 'award_ids'})
        
        # 如果提供了荣誉ID列表，验证并添加荣誉
        if company.award_ids:
            awards = []
            for award_id in company.award_ids:
                award = db.query(models.Award).filter(models.Award.id == award_id).first()
                if not award:
                    raise HTTPException(status_code=404, detail=f"Award {award_id} not found")
                awards.append(award)
            db_company.awards = awards
        
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        logger.info(f"公司创建成功: ID={db_company.id}")
        return db_company
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"创建公司失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/companies/{company_id}", response_model=schemas.Company)
def update_company(company_id: int, company: schemas.CompanyCreate, db: Session = Depends(get_db)):
    """更新公司信息"""
    try:
        logger.info(f"更新公司: ID={company_id}")
        db_company = db.query(models.Company).filter(models.Company.id == company_id).first()
        if not db_company:
            logger.warning(f"未找到公司: ID={company_id}")
            raise HTTPException(status_code=404, detail="Company not found")
        
        # 更新基本信息
        for key, value in company.model_dump(exclude={'award_ids'}).items():
            setattr(db_company, key, value)
        
        # 更新荣誉关联
        if company.award_ids is not None:  # 允许清空荣誉列表
            awards = []
            for award_id in company.award_ids:
                award = db.query(models.Award).filter(models.Award.id == award_id).first()
                if not award:
                    raise HTTPException(status_code=404, detail=f"Award {award_id} not found")
                awards.append(award)
            db_company.awards = awards
        
        db.commit()
        db.refresh(db_company)
        logger.info(f"公司更新成功: ID={company_id}")
        return db_company
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"更新公司失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/companies/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    """删除公司"""
    db_company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    db.delete(db_company)
    db.commit()
    return {"message": "Company deleted successfully"}

@router.get("/videos", response_model=List[schemas.Video])
def get_videos(db: Session = Depends(get_db)):
    """获取所有视频列表"""
    return db.query(models.Video).all()

@router.get("/videos/{video_id}", response_model=schemas.Video)
def get_video(video_id: int, db: Session = Depends(get_db)):
    """获取单个视频详情"""
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@router.post("/videos", response_model=schemas.Video)
def create_video(video: schemas.VideoCreate, db: Session = Depends(get_db)):
    """创建新视频"""
    db_video = models.Video(**video.model_dump())
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

@router.put("/videos/{video_id}", response_model=schemas.Video)
def update_video(video_id: int, video: schemas.VideoCreate, db: Session = Depends(get_db)):
    """更新视频信息"""
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    for key, value in video.model_dump().items():
        setattr(db_video, key, value)
    
    db.commit()
    db.refresh(db_video)
    return db_video

@router.delete("/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    """删除视频"""
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    db.delete(db_video)
    db.commit()
    return {"message": "Video deleted successfully"}

@router.get("/visitor-records", response_model=List[schemas.VisitorRecord])
def get_visitor_records(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取参观记录列表"""
    query = db.query(models.VisitorRecord)
    
    if start_date:
        query = query.filter(models.VisitorRecord.visit_date >= start_date)
    if end_date:
        query = query.filter(models.VisitorRecord.visit_date <= end_date)
    
    return query.all()

@router.get("/visitor-records/{record_id}", response_model=schemas.VisitorRecord)
def get_visitor_record(record_id: int, db: Session = Depends(get_db)):
    """获取单个参观记录详情"""
    record = db.query(models.VisitorRecord).filter(models.VisitorRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Visitor record not found")
    return record

@router.post("/visitor-records", response_model=schemas.VisitorRecord)
def create_visitor_record(record: schemas.VisitorRecordCreate, db: Session = Depends(get_db)):
    """创建新参观记录"""
    db_record = models.VisitorRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@router.put("/visitor-records/{record_id}", response_model=schemas.VisitorRecord)
def update_visitor_record(record_id: int, record: schemas.VisitorRecordCreate, db: Session = Depends(get_db)):
    """更新参观记录"""
    db_record = db.query(models.VisitorRecord).filter(models.VisitorRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Visitor record not found")
    
    for key, value in record.model_dump().items():
        setattr(db_record, key, value)
    
    db.commit()
    db.refresh(db_record)
    return db_record

@router.delete("/visitor-records/{record_id}")
def delete_visitor_record(record_id: int, db: Session = Depends(get_db)):
    """删除参观记录"""
    db_record = db.query(models.VisitorRecord).filter(models.VisitorRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Visitor record not found")
    
    db.delete(db_record)
    db.commit()
    return {"message": "Visitor record deleted successfully"}

@router.get("/data-types", response_model=List[schemas.DataType])
def get_data_types(db: Session = Depends(get_db)):
    """获取所有数据类型列表"""
    return db.query(models.DataType).all()

@router.get("/data-types/{type_id}", response_model=schemas.DataType)
def get_data_type(type_id: int, db: Session = Depends(get_db)):
    """获取单个数据类型详情"""
    data_type = db.query(models.DataType).filter(models.DataType.id == type_id).first()
    if not data_type:
        raise HTTPException(status_code=404, detail="Data type not found")
    return data_type

@router.post("/data-types", response_model=schemas.DataType)
def create_data_type(data_type: schemas.DataTypeCreate, db: Session = Depends(get_db)):
    """创建新数据类型"""
    db_data_type = models.DataType(**data_type.model_dump())
    db.add(db_data_type)
    db.commit()
    db.refresh(db_data_type)
    return db_data_type

@router.put("/data-types/{type_id}", response_model=schemas.DataType)
def update_data_type(type_id: int, data_type: schemas.DataTypeCreate, db: Session = Depends(get_db)):
    """更新数据类型"""
    db_data_type = db.query(models.DataType).filter(models.DataType.id == type_id).first()
    if not db_data_type:
        raise HTTPException(status_code=404, detail="Data type not found")
    
    for key, value in data_type.model_dump().items():
        setattr(db_data_type, key, value)
    
    db.commit()
    db.refresh(db_data_type)
    return db_data_type

@router.delete("/data-types/{type_id}")
def delete_data_type(type_id: int, db: Session = Depends(get_db)):
    """删除数据类型"""
    db_data_type = db.query(models.DataType).filter(models.DataType.id == type_id).first()
    if not db_data_type:
        raise HTTPException(status_code=404, detail="Data type not found")
    
    db.delete(db_data_type)
    db.commit()
    return {"message": "Data type deleted successfully"}

@router.get("/data-records", response_model=schemas.PaginatedResponse[schemas.DataRecord])
def get_data_records(
    page: int = 1,
    page_size: int = 10,
    data_type_id: Optional[int] = None,
    robot_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取数据采集记录列表"""
    try:
        logger.info(f"获取数据采集记录列表: page={page}, page_size={page_size}")
        
        # 构建查询
        query = db.query(models.DataRecord).options(
            joinedload(models.DataRecord.data_type),
            joinedload(models.DataRecord.robot)
        )
        
        # 添加过滤条件
        if data_type_id:
            query = query.filter(models.DataRecord.data_type_id == data_type_id)
        if robot_id:
            query = query.filter(models.DataRecord.robot_id == robot_id)
        if start_date:
            query = query.filter(models.DataRecord.collect_date >= start_date)
        if end_date:
            query = query.filter(models.DataRecord.collect_date <= end_date)
        
        # 计算总数
        total = query.count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        records = query.offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(records)} 条记录")
        
        return schemas.PaginatedResponse(
            items=records,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取数据采集记录列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-records/{record_id}", response_model=schemas.DataRecord)
def get_data_record(record_id: int, db: Session = Depends(get_db)):
    """获取单个数据采集记录详情"""
    try:
        logger.info(f"获取数据采集记录详情: ID={record_id}")
        record = db.query(models.DataRecord).options(
            joinedload(models.DataRecord.data_type),
            joinedload(models.DataRecord.robot)
        ).filter(models.DataRecord.id == record_id).first()
        if not record:
            logger.warning(f"未找到数据采集记录: ID={record_id}")
            raise HTTPException(status_code=404, detail="Data record not found")
        return record
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取数据采集记录详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data-records", response_model=schemas.DataRecord)
def create_data_record(record: schemas.DataRecordCreate, db: Session = Depends(get_db)):
    """创建新数据采集记录"""
    db_record = models.DataRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@router.put("/data-records/{record_id}", response_model=schemas.DataRecord)
def update_data_record(record_id: int, record: schemas.DataRecordCreate, db: Session = Depends(get_db)):
    """更新数据采集记录"""
    db_record = db.query(models.DataRecord).filter(models.DataRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Data record not found")
    
    for key, value in record.model_dump().items():
        setattr(db_record, key, value)
    
    db.commit()
    db.refresh(db_record)
    return db_record

@router.delete("/data-records/{record_id}")
def delete_data_record(record_id: int, db: Session = Depends(get_db)):
    """删除数据采集记录"""
    db_record = db.query(models.DataRecord).filter(models.DataRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Data record not found")
    
    db.delete(db_record)
    db.commit()
    return {"message": "Data record deleted successfully"}

@router.get("/web-configs", response_model=List[schemas.WebConfig])
def get_web_configs(db: Session = Depends(get_db)):
    """获取所有网页配置信息"""
    return db.query(models.WebConfig).all()

@router.get("/web-configs/{config_id}", response_model=schemas.WebConfig)
def get_web_config(config_id: int, db: Session = Depends(get_db)):
    """获取单个网页配置信息"""
    config = db.query(models.WebConfig).filter(models.WebConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Web config not found")
    return config

@router.post("/web-configs", response_model=schemas.WebConfig)
def create_web_config(config: schemas.WebConfigCreate, db: Session = Depends(get_db)):
    """创建新网页配置信息"""
    db_config = models.WebConfig(**config.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.put("/web-configs/{config_id}", response_model=schemas.WebConfig)
def update_web_config(config_id: int, config: schemas.WebConfigCreate, db: Session = Depends(get_db)):
    """更新网页配置信息"""
    db_config = db.query(models.WebConfig).filter(models.WebConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Web config not found")
    
    for key, value in config.model_dump().items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config

@router.delete("/web-configs/{config_id}")
def delete_web_config(config_id: int, db: Session = Depends(get_db)):
    """删除网页配置信息"""
    db_config = db.query(models.WebConfig).filter(models.WebConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Web config not found")
    
    db.delete(db_config)
    db.commit()
    return {"message": "Web config deleted successfully"}

@router.post("/upload/image", response_model=schemas.FileResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    上传图片文件
    
    Args:
        file: 上传的图片文件
        
    Returns:
        dict: 包含文件URL的响应
    """
    # 验证文件类型
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只允许上传图片文件")
    
    # 保存文件
    file_url = await save_upload_file(file)
    
    return {"url": file_url} 