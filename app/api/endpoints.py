from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from app.database.database import get_db
from app.models import models
from app.schemas import schemas
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import logging
from app.utils.file_handler import save_upload_file
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.encoders import jsonable_encoder
import random
import os
import mimetypes

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 自定义错误响应
def error_response(status_code: int, detail: str, error_type: str = "error"):
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "status": "error",
            "error_type": error_type,
            "detail": detail
        })
    )

@router.get("/robots/carousel", response_model=List[schemas.Robot])
def get_carousel_robots(db: Session = Depends(get_db)):
    """获取所有轮播机器人列表"""
    try:
        logger.info("获取轮播机器人列表")
        
        # 查询所有is_carousel为true的机器人
        robots = db.query(models.Robot).options(
            joinedload(models.Robot.company),
            joinedload(models.Robot.training_field),
            joinedload(models.Robot.data_records)
        ).filter(
            models.Robot.is_carousel == True
        ).order_by(
            models.Robot.carousel_add_time.desc()  # 按轮播添加时间倒序排序
        ).all()
        
        logger.info(f"找到 {len(robots)} 个轮播机器人")
        return robots
        
    except Exception as e:
        logger.error(f"获取轮播机器人列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/robots/status-stats", response_model=Dict[str, int])
def get_robot_status_stats(
    robot_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """统计机器人的在线、离线、故障状态数量，以及总数"""
    try:
        logger.info("开始统计机器人状态分布")
        
        # 构建基础查询
        query = db.query(
            models.Robot.status,
            func.count(models.Robot.id)
        )
        
        # 如果提供了robot_id，则只统计该机器人
        if robot_id:
            query = query.filter(models.Robot.id == robot_id)
            
        # 执行查询并按状态分组
        status_counts = query.group_by(models.Robot.status).all()
        
        # 创建状态计数字典，处理可能的空值
        status_dict = {status: count for status, count in status_counts if status}
        
        # 计算总数
        total = sum(status_dict.values())
        
        # 组装结果，使用更灵活的状态映射
        results = {
            "online": sum(count for status, count in status_counts if status and "在线" in status),
            "offline": sum(count for status, count in status_counts if status and "离线" in status),
            "fault": sum(count for status, count in status_counts if status and "故障" in status),
            "total": total
        }
        
        logger.info(f"状态统计完成: {results}")
        return results
        
    except Exception as e:
        logger.error(f"统计机器人状态分布失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/robots/skill-stats", response_model=List[Dict[str, Any]])
def get_robot_skill_stats(
    robot_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """统计机器人不同skill的数量，固定四种：操作性能、移动性能、交互性能、其他"""
    try:
        logger.info("开始统计机器人技能分布")
        fixed_skills = ["操作性能", "移动性能", "交互性能", "其他"]
        
        # 构建基础查询
        query = db.query(
            models.Robot.skills,
            func.count(models.Robot.id)
        )
        
        # 如果提供了robot_id，则只统计该机器人
        if robot_id:
            query = query.filter(models.Robot.id == robot_id)
            
        # 执行查询并按技能分组
        skill_counts = query.group_by(models.Robot.skills).all()
        
        # 创建技能计数字典，处理可能的空值
        skill_count_dict = {skill: count for skill, count in skill_counts if skill}
        
        # 组装结果，保证四种技能都出现
        results = []
        for skill in fixed_skills:
            # 查找包含该技能关键词的记录
            count = sum(count for s, count in skill_counts if s and skill in s)
            results.append({
                "skill": skill,
                "count": count
            })
            
        logger.info(f"技能统计完成: {results}")
        return results
    except Exception as e:
        logger.error(f"统计机器人技能分布失败: {str(e)}")
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
        
        # 获取分页数据，优先显示轮播的机器人
        robots = query.order_by(
            models.Robot.is_carousel.desc(),
            models.Robot.carousel_add_time.desc(),
            models.Robot.create_date.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
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

@router.get("/training-fields/robot-stats", response_model=List[Dict[str, Any]])
def get_training_fields_robot_stats(db: Session = Depends(get_db)):
    """获取所有训练场的机器人数量统计"""
    try:
        logger.info("开始统计训练场机器人数量")
        
        # 获取所有训练场
        training_fields = db.query(models.TrainingField).all()
        
        # 获取每个训练场的机器人数量
        field_robot_counts = db.query(
            models.Robot.training_field_id,
            func.count(models.Robot.id)
        ).group_by(models.Robot.training_field_id).all()
        
        # 创建训练场机器人数量的字典，方便查找
        robot_counts_dict = {field_id: count for field_id, count in field_robot_counts}
        
        # 生成结果
        results = []
        for field in training_fields:
            results.append({
                "field_id": field.id,
                "field_name": field.name,
                "robot_count": robot_counts_dict.get(field.id, 0)  # 如果没有机器人，则为0
            })
        
        logger.info(f"统计完成，共找到 {len(results)} 个训练场")
        return results
        
    except Exception as e:
        logger.error(f"统计训练场机器人数量失败: {str(e)}")
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

@router.get("/awards", response_model=schemas.PaginatedResponse[schemas.Award])
def get_awards(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """获取所有荣誉证书列表"""
    try:
        logger.info(f"获取荣誉列表: page={page}, page_size={page_size}")
        
        # 计算总数
        total = db.query(models.Award).count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        awards = db.query(models.Award).offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(awards)} 个荣誉")
        
        return schemas.PaginatedResponse(
            items=awards,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取荣誉列表失败: {str(e)}")
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
    name: Optional[str] = None,
    is_carousel: Optional[bool] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取所有公司列表"""
    try:
        logger.info(f"获取公司列表: page={page}, page_size={page_size}, name={name}, is_carousel={is_carousel}")
        
        # 构建基础查询
        query = db.query(models.Company).options(
            joinedload(models.Company.awards)
        )
        
        # 添加筛选条件
        if name:
            query = query.filter(models.Company.name.ilike(f"%{name}%"))
        
        if is_carousel is not None:
            query = query.filter(models.Company.is_carousel == is_carousel)
        
        if start_time:
            query = query.filter(models.Company.create_time >= start_time)
        
        if end_time:
            query = query.filter(models.Company.create_time <= end_time)
        
        # 计算总数
        total = query.count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        companies = query.order_by(
            models.Company.is_carousel.desc(),
            models.Company.create_time.desc()
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
        company_data = company.model_dump()
        # 设置创建时间为当前时间戳字符串
        company_data['create_time'] = str(int(datetime.now().timestamp()))
        db_company = models.Company(**{k: v for k, v in company_data.items() if k != 'award_ids'})
        
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
        company_data = company.model_dump(exclude={'award_ids'})
        # 更新创建时间为当前时间戳字符串
        company_data['create_time'] = str(int(datetime.now().timestamp()))
        for key, value in company_data.items():
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

@router.get("/videos/carousel", response_model=schemas.PaginatedResponse[schemas.Video])
def get_carousel_videos(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """获取轮播视频列表"""
    try:
        logger.info(f"获取轮播视频列表: page={page}, page_size={page_size}")
        
        # 计算总数
        total = db.query(models.Video).filter(models.Video.is_carousel == True).count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        videos = db.query(models.Video).filter(
            models.Video.is_carousel == True
        ).order_by(
            models.Video.create_time.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(videos)} 个轮播视频")
        
        return schemas.PaginatedResponse(
            items=videos,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取轮播视频列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/videos/upload", response_model=schemas.FileResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传视频文件
    
    Args:
        file: 上传的视频文件
        
    Returns:
        dict: 包含文件URL的响应
    """
    try:
        logger.info(f"开始上传视频文件: {file.filename}")
        
        # 验证文件类型
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="只允许上传视频文件")
            
        # 验证文件大小（限制为100MB）
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > 100 * 1024 * 1024:  # 100MB
                raise HTTPException(status_code=400, detail="视频文件大小不能超过100MB")
        
        # 重置文件指针
        await file.seek(0)
        
        # 生成文件名
        timestamp = int(datetime.now().timestamp())
        file_extension = file.filename.split('.')[-1]
        new_filename = f"{timestamp}_{file.filename}"
        
        # 确保上传目录存在
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "uploads", "videos")
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(upload_dir, new_filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 返回文件URL
        file_url = f"/static/uploads/videos/{new_filename}"
        logger.info(f"视频文件上传成功: {file_url}")
        
        return {"url": file_url}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"视频文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"视频文件上传失败: {str(e)}")

@router.post("/videos", response_model=schemas.Video)
async def create_video(
    video: schemas.VideoCreate,
    db: Session = Depends(get_db)
):
    """创建新视频记录"""
    try:
        logger.info(f"开始创建视频记录: {video.model_dump()}")
        
        # 创建视频记录
        video_data = video.model_dump()
        video_data["create_time"] = str(int(datetime.now().timestamp()))
        
        logger.info(f"创建视频记录: {video_data}")
        
        db_video = models.Video(**video_data)
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        
        logger.info(f"视频记录创建成功: ID={db_video.id}")
        return db_video
        
    except HTTPException as he:
        logger.error(f"创建视频记录失败 (HTTP异常): {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"创建视频记录失败 (其他异常): {str(e)}")
        if hasattr(e, 'errors'):
            logger.error(f"验证错误详情: {e.errors()}")
        raise HTTPException(status_code=500, detail=f"创建视频记录失败: {str(e)}")

@router.get("/videos/stream/{video_id}")
async def stream_video(video_id: int, db: Session = Depends(get_db)):
    """获取视频流
    
    Args:
        video_id: 视频ID
        
    Returns:
        StreamingResponse: 视频流
    """
    try:
        # 获取视频记录
        video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
            
        # 获取视频文件路径
        if video.type == 'LOCAL':
            # 对于本地视频，使用相对路径
            video_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                video.url.lstrip('/')
            )
        else:
            video_path = video.url
            
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"视频文件不存在: {video_path}")
            
        # 获取文件类型
        content_type, _ = mimetypes.guess_type(video_path)
        if not content_type:
            content_type = "video/mp4"  # 默认类型
            
        # 返回视频流，添加CORS头
        response = FileResponse(
            video_path,
            media_type=content_type,
            filename=video.name
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取视频流失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取视频流失败: {str(e)}")

@router.get("/videos/list", response_model=List[schemas.Video])
def get_videos_list(
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取视频列表
    
    Args:
        type: 视频类型（可选）
        
    Returns:
        List[Video]: 视频列表
    """
    try:
        query = db.query(models.Video)
        
        if type:
            query = query.filter(models.Video.type == type)
            
        videos = query.order_by(models.Video.create_time.desc()).all()
        return videos
        
    except Exception as e:
        logger.error(f"获取视频列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取视频列表失败: {str(e)}")

@router.get("/videos/{video_id}", response_model=schemas.Video)
def get_video(video_id: int, db: Session = Depends(get_db)):
    """获取单个视频详情"""
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@router.put("/videos/{video_id}", response_model=schemas.Video)
async def update_video(
    video_id: int,
    video: schemas.VideoCreate,
    db: Session = Depends(get_db)
):
    """更新视频信息"""
    try:
        logger.info(f"开始更新视频: ID={video_id}")
        
        # 查找视频记录
        db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not db_video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 更新视频信息
        video_data = video.model_dump()
        # 更新创建时间为当前时间戳
        video_data['create_time'] = str(int(datetime.now().timestamp()))
        for key, value in video_data.items():
            setattr(db_video, key, value)
        
        db.commit()
        db.refresh(db_video)
        
        logger.info(f"视频更新成功: ID={video_id}")
        return db_video
        
    except HTTPException as he:
        logger.error(f"更新视频失败 (HTTP异常): {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"更新视频失败 (其他异常): {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新视频失败: {str(e)}")

@router.get("/videos", response_model=schemas.PaginatedResponse[schemas.Video])
def get_videos(
    page: int = 1,
    page_size: int = 10,
    name: Optional[str] = None,
    video_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取所有视频列表"""
    try:
        logger.info(f"获取视频列表: page={page}, page_size={page_size}, name={name}, video_type={video_type}")
        
        # 构建查询
        query = db.query(models.Video)
        
        # 添加筛选条件
        if name:
            query = query.filter(models.Video.name.like(f"%{name}%"))
        if video_type:
            query = query.filter(models.Video.type == video_type)
        
        # 计算总数
        total = query.count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        videos = query.order_by(
            models.Video.is_carousel.desc(),
            models.Video.create_time.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        # 处理视频URL
        for video in videos:
            if video.type == 'LOCAL' and video.url:
                # 确保本地视频URL以/开头
                video.url = video.url if video.url.startswith('/') else f"/{video.url}"
        
        logger.info(f"找到 {len(videos)} 个视频")
        
        return schemas.PaginatedResponse(
            items=videos,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取视频列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/visitor-records/stats", response_model=Dict[str, Any])
def get_visitor_stats(db: Session = Depends(get_db)):
    """统计访客数量，包括每日、本周和本月的统计"""
    try:
        logger.info("开始统计访客数量")
        
        # 获取当前时间戳和日期字符串
        now = datetime.now()
        current_timestamp = int(now.timestamp())
        today_str = now.strftime("%Y-%m-%d")
        
        # 检查今天是否有数据（使用时间戳范围比较）
        today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        today_end = int(datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).timestamp())
        
        today_record = db.query(models.VisitorRecord).filter(
            models.VisitorRecord.visit_date.between(str(today_start), str(today_end))
        ).first()
        
        # 如果今天没有数据，则创建一条新记录
        if not today_record:
            logger.info("今天还没有访客记录，创建新记录")
            new_count = random.randint(0, 200)
            new_record = models.VisitorRecord(
                visit_date=str(current_timestamp),
                visitor_count=new_count
            )
            db.add(new_record)
            db.commit()
            logger.info(f"创建新的访客记录: {new_count}")
        
        # 计算10天前的时间戳
        ten_days_ago = int((now - timedelta(days=10)).timestamp())
        
        # 计算本周开始的时间戳（周一）
        week_start = now - timedelta(days=now.weekday())
        week_start_timestamp = int(week_start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        
        # 计算本月开始的时间戳
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_start_timestamp = int(month_start.timestamp())
        
        # 查询最近10天的访客记录
        visitor_records = db.query(
            models.VisitorRecord.visit_date,
            models.VisitorRecord.visitor_count
        ).filter(
            models.VisitorRecord.visit_date >= str(ten_days_ago)
        ).order_by(models.VisitorRecord.visit_date).all()
        
        # 计算本周访客数量
        week_visitors = db.query(
            func.sum(models.VisitorRecord.visitor_count)
        ).filter(
            models.VisitorRecord.visit_date >= str(week_start_timestamp)
        ).scalar() or 0
        
        # 计算本月访客数量
        month_visitors = db.query(
            func.sum(models.VisitorRecord.visitor_count)
        ).filter(
            models.VisitorRecord.visit_date >= str(month_start_timestamp)
        ).scalar() or 0
        
        # 创建最近10天的日期列表
        date_list = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10)]
        date_list.reverse()  # 从早到晚排序
        
        # 创建日期到访客数的映射
        visitor_dict = {
            datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d"): count 
            for timestamp, count in visitor_records
        }
        
        # 组装每日访客数据，确保最近10天都有数据
        daily_stats = []
        for date in date_list:
            daily_stats.append({
                "date": date,
                "count": visitor_dict.get(date, 0)  # 如果没有数据，显示0
            })
        
        # 添加日志输出，帮助调试
        logger.info(f"查询到的访客记录: {visitor_records}")
        logger.info(f"本周访客数量: {week_visitors}")
        logger.info(f"本月访客数量: {month_visitors}")
        
        results = {
            "daily_stats": daily_stats,
            "week_total": int(week_visitors),
            "month_total": int(month_visitors)
        }
        
        logger.info(f"访客统计完成: {results}")
        return results
        
    except Exception as e:
        logger.error(f"统计访客数量失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/visitor-records", response_model=schemas.PaginatedResponse[schemas.VisitorRecord])
def get_visitor_records(
    page: int = 1,
    page_size: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取参观记录列表"""
    try:
        logger.info(f"获取参观记录列表: page={page}, page_size={page_size}")
        
        # 构建查询
        query = db.query(models.VisitorRecord)
        
        if start_date:
            query = query.filter(models.VisitorRecord.visit_date >= start_date)
        if end_date:
            query = query.filter(models.VisitorRecord.visit_date <= end_date)
        
        # 计算总数
        total = query.count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        records = query.offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(records)} 条参观记录")
        
        return schemas.PaginatedResponse(
            items=records,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取参观记录列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/data-types", response_model=schemas.PaginatedResponse[schemas.DataType])
def get_data_types(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """获取所有数据类型列表"""
    try:
        logger.info(f"获取数据类型列表: page={page}, page_size={page_size}")
        
        # 计算总数
        total = db.query(models.DataType).count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        types = db.query(models.DataType).offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(types)} 个数据类型")
        
        return schemas.PaginatedResponse(
            items=types,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取数据类型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    try:
        logger.info("创建新数据类型")
        
        # 检查名称是否已存在
        existing_type = db.query(models.DataType).filter(
            models.DataType.name == data_type.name
        ).first()
        
        if existing_type:
            logger.warning(f"数据类型名称已存在: {data_type.name}")
            return error_response(
                status_code=400,
                detail=f"数据类型名称 '{data_type.name}' 已存在",
                error_type="duplicate_name"
            )
        
        db_data_type = models.DataType(**data_type.model_dump())
        db.add(db_data_type)
        db.commit()
        db.refresh(db_data_type)
        
        logger.info(f"数据类型创建成功: ID={db_data_type.id}")
        return db_data_type
    except Exception as e:
        logger.error(f"创建数据类型失败: {str(e)}")
        return error_response(
            status_code=500,
            detail=f"创建数据类型失败: {str(e)}",
            error_type="server_error"
        )

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

@router.get("/data-records/type-stats", response_model=Dict[str, Any])
def get_data_records_type_stats(db: Session = Depends(get_db)):
    """统计不同类型的数据采集记录数量（count字段总和）"""
    try:
        logger.info("开始统计数据采集记录类型分布")
        
        # 获取所有数据类型
        data_types = db.query(models.DataType).all()
        
        # 获取今天的日期
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 查询各类型的数据记录count总和
        type_counts = db.query(
            models.DataRecord.data_type_id,
            func.sum(models.DataRecord.count)  # 使用sum而不是count
        ).group_by(models.DataRecord.data_type_id).all()
        
        # 查询今日各类型的数据记录count总和
        today_type_counts = db.query(
            models.DataRecord.data_type_id,
            func.sum(models.DataRecord.count)
        ).filter(
            models.DataRecord.collect_date.like(f"{today}%")
        ).group_by(models.DataRecord.data_type_id).all()
        
        # 创建类型计数字典
        type_count_dict = {type_id: count for type_id, count in type_counts if count is not None}
        today_type_count_dict = {type_id: count for type_id, count in today_type_counts if count is not None}
        
        # 计算总采集数量
        total_count = sum(type_count_dict.values())
        # 计算今日采集数量
        today_total_count = sum(today_type_count_dict.values())
        
        # 组装结果
        type_stats = []
        for data_type in data_types:
            type_stats.append({
                "type_id": data_type.id,
                "type_name": data_type.name,
                "count": int(type_count_dict.get(data_type.id, 0)),  # 如果没有记录，则为0
                "today_count": int(today_type_count_dict.get(data_type.id, 0))  # 今日采集数量
            })
        
        results = {
            "type_stats": type_stats,
            "total_count": total_count,
            "today_count": today_total_count
        }
        
        logger.info(f"数据采集记录类型统计完成: {results}")
        return results
        
    except Exception as e:
        logger.error(f"统计数据采集记录类型分布失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    try:
        logger.info("创建新数据采集记录")
        
        # 验证数据类型是否存在
        data_type = db.query(models.DataType).filter(models.DataType.id == record.data_type_id).first()
        if not data_type:
            logger.warning(f"未找到数据类型: ID={record.data_type_id}")
            return error_response(
                status_code=404,
                detail=f"未找到ID为{record.data_type_id}的数据类型",
                error_type="data_type_not_found"
            )
        
        # 验证机器人是否存在
        robot = db.query(models.Robot).filter(models.Robot.id == record.robot_id).first()
        if not robot:
            logger.warning(f"未找到机器人: ID={record.robot_id}")
            return error_response(
                status_code=404,
                detail=f"未找到ID为{record.robot_id}的机器人",
                error_type="robot_not_found"
            )
        
        db_record = models.DataRecord(**record.model_dump())
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        logger.info(f"数据采集记录创建成功: ID={db_record.id}")
        return db_record
    except Exception as e:
        logger.error(f"创建数据采集记录失败: {str(e)}")
        return error_response(
            status_code=500,
            detail=f"创建数据采集记录失败: {str(e)}",
            error_type="server_error"
        )

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

@router.get("/web-configs", response_model=schemas.PaginatedResponse[schemas.WebConfig])
def get_web_configs(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """获取所有网页配置信息"""
    try:
        logger.info(f"获取网页配置列表: page={page}, page_size={page_size}")
        
        # 计算总数
        total = db.query(models.WebConfig).count()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        configs = db.query(models.WebConfig).offset((page - 1) * page_size).limit(page_size).all()
        
        logger.info(f"找到 {len(configs)} 个网页配置")
        
        return schemas.PaginatedResponse(
            items=configs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取网页配置列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/robot-types/analysis", response_model=Dict[str, List[schemas.RobotTypeAnalysis]])
def analyze_robot_types(db: Session = Depends(get_db)):
    """分析机器人种类分布"""
    try:
        logger.info("开始分析机器人种类分布")
        
        # 获取当前月份的开始和结束时间戳
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        month_end = next_month - timedelta(days=1)
        
        month_start_timestamp = str(int(month_start.timestamp()))
        month_end_timestamp = str(int(month_end.timestamp()))
        
        logger.info(f"查询当月数据范围: {month_start_timestamp} - {month_end_timestamp}")
        
        # 获取所有机器人种类及其数量
        robot_types = db.query(
            models.Robot.industry_type,
            func.count(models.Robot.id)
        ).group_by(models.Robot.industry_type).all()
        
        # 获取当月受训机器人种类及其数量
        training_robot_types = db.query(
            models.Robot.industry_type,
            func.count(models.Robot.id)
        ).filter(
            models.Robot.create_date.between(month_start_timestamp, month_end_timestamp)
        ).group_by(models.Robot.industry_type).all()
        
        # 计算总数
        total_robots = sum(count for _, count in robot_types)
        total_training_robots = sum(count for _, count in training_robot_types)
        
        logger.info(f"当月机器人总数: {total_training_robots}")
        
        # 创建当月受训机器人类型的字典，方便查找
        training_types_dict = {type_: count for type_, count in training_robot_types}
        
        # 计算每种类型的百分比（全部机器人）
        all_analysis_results = []
        for type_, count in robot_types:
            percentage = int((count / total_robots * 100)) if total_robots > 0 else 0
            all_analysis_results.append(schemas.RobotTypeAnalysis(
                type=type_,
                count=count,
                percentage=percentage
            ))
        
        # 计算每种类型的百分比（当月受训机器人）
        training_analysis_results = []
        for type_, count in robot_types:  # 使用所有类型
            training_count = training_types_dict.get(type_, 0)  # 如果没有当月数据，则为0
            percentage = int((training_count / total_training_robots * 100)) if total_training_robots > 0 else 0
            training_analysis_results.append(schemas.RobotTypeAnalysis(
                type=type_,
                count=training_count,
                percentage=percentage
            ))
        
        logger.info(f"分析完成，共找到 {len(all_analysis_results)} 种机器人类型")
        
        return {
            "all_robots": all_analysis_results,
            "training_robots": training_analysis_results
        }
        
    except Exception as e:
        logger.error(f"分析机器人种类分布失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entrance-records/stats", response_model=Dict[str, Any])
def get_entrance_stats(db: Session = Depends(get_db)):
    """模拟入场人数统计，包括每日、本周和本月的统计"""
    try:
        logger.info("开始统计入场人数")
        
        # 获取当前时间戳
        now = datetime.now()
        current_timestamp = int(now.timestamp())
        
        # 计算10天前的时间戳
        ten_days_ago = int((now - timedelta(days=10)).timestamp())
        
        # 计算本周开始的时间戳（周一）
        week_start = now - timedelta(days=now.weekday())
        week_start_timestamp = int(week_start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        
        # 计算本月开始的时间戳
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_start_timestamp = int(month_start.timestamp())
        
        # 生成最近10天的模拟数据
        daily_stats = []
        week_total = 0
        month_total = 0
        
        for i in range(10):
            # 生成随机人数（0-200之间）
            count = random.randint(0, 200)
            # 计算日期（从今天往前推）
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            timestamp = int(date.timestamp())
            
            daily_stats.append({
                "date": date_str,
                "count": count
            })
            
            # 累加本周和本月的数据
            if timestamp >= week_start_timestamp:
                week_total += count
            if timestamp >= month_start_timestamp:
                month_total += count
        
        # 按日期排序（从早到晚）
        daily_stats.sort(key=lambda x: x["date"])
        
        results = {
            "daily_stats": daily_stats,
            "week_total": week_total,
            "month_total": month_total
        }
        
        logger.info(f"入场人数统计完成: {results}")
        return results
        
    except Exception as e:
        logger.error(f"统计入场人数失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/videos/{video_id}")
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    """删除视频"""
    try:
        logger.info(f"开始删除视频: ID={video_id}")
        
        # 查找视频记录
        video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 如果是本地视频，删除文件
        if video.type == 'LOCAL' and video.url:
            try:
                file_path = video.url.lstrip('/')  # 移除开头的斜杠
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"删除视频文件: {file_path}")
            except Exception as e:
                logger.error(f"删除视频文件失败: {str(e)}")
        
        # 删除数据库记录
        db.delete(video)
        db.commit()
        
        logger.info(f"视频删除成功: ID={video_id}")
        return {"message": "视频删除成功"}
        
    except HTTPException as he:
        logger.error(f"删除视频失败 (HTTP异常): {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"删除视频失败 (其他异常): {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除视频失败: {str(e)}") 